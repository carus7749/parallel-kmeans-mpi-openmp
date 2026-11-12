#include "kmeans.hpp"
#include <climits>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#ifdef USE_MPI
#include <mpi.h>
#endif
#ifdef USE_OMP
#include <omp.h>
#endif

struct Options {
    uint64_t n=10000, seed=42; int d=8,k=5,iterations=100,threads=1;
    double tol=1e-6; bool fixed=false,details=false; std::string input, init;
};
uint64_t integer(const std::string& s) {
    if(s.empty() || s.find_first_not_of("0123456789")!=std::string::npos)
        throw std::runtime_error("Expected unsigned integer: "+s);
    size_t used=0; auto x=std::stoull(s,&used);
    if(used!=s.size()) throw std::runtime_error("Invalid integer");
    return x;
}
int small_integer(const std::string& s) {
    auto x=integer(s); if(x>INT_MAX) throw std::runtime_error("Integer exceeds INT_MAX");
    return int(x);
}
Options parse(int argc,char** argv) {
    Options o;
    for(int i=1;i<argc;++i) {
        std::string a=argv[i];
        if(a=="--fixed") {o.fixed=true;continue;}
        if(a=="--details") {o.details=true;continue;}
        if(i+1==argc) throw std::runtime_error("Missing value for "+a);
        std::string v=argv[++i];
        if(a=="--n") o.n=integer(v);
        else if(a=="--d") o.d=small_integer(v);
        else if(a=="--k") o.k=small_integer(v);
        else if(a=="--seed") o.seed=integer(v);
        else if(a=="--iterations") o.iterations=small_integer(v);
        else if(a=="--threads") o.threads=small_integer(v);
        else if(a=="--input") o.input=v;
        else if(a=="--init") o.init=v;
        else if(a=="--tol") {
            size_t pos; o.tol=std::stod(v,&pos);
            if(pos!=v.size()) throw std::runtime_error("Invalid tolerance");
        } else throw std::runtime_error("Unknown option: "+a);
    }
    if(!o.n||o.d<1||o.k<1||uint64_t(o.k)>o.n||o.iterations<1||o.threads<1||
       !std::isfinite(o.tol)||o.tol<0) throw std::runtime_error("Invalid dimensions, iterations, threads or tolerance");
    // Conservative portable bound: ordinary MPI counts and test-output gathers use int.
    if(o.n>uint64_t(INT_MAX)/uint64_t(o.d)) throw std::runtime_error("N*d must not exceed INT_MAX");
    if(uint64_t(o.threads)>SIZE_MAX/(size_t(o.k)*o.d*sizeof(double)))
        throw std::runtime_error("Thread buffer size overflow");
#ifndef USE_OMP
    if(o.threads!=1) throw std::runtime_error("This executable requires --threads 1");
#endif
    return o;
}
std::vector<double> read_values(const std::string& path,size_t count) {
    std::ifstream in(path); if(!in) throw std::runtime_error("Cannot open "+path);
    std::vector<double> x; double v;
    while(in>>v) {
        if(!std::isfinite(v)||std::abs(v)>1e100) throw std::runtime_error("Invalid or excessive numeric value");
        x.push_back(v); if(x.size()>count) throw std::runtime_error("Too many input values");
    }
    if(!in.eof()||x.size()!=count) throw std::runtime_error("Input must contain exactly the requested finite numeric values");
    return x;
}
void array(std::ostream& out,const std::vector<double>& v) {
    out<<'['; for(size_t i=0;i<v.size();++i) {if(i)out<<',';out<<v[i];}out<<']';
}

int main(int argc,char** argv) {
    int rank=0,ranks=1;
#ifdef USE_MPI
    int provided=0; MPI_Init_thread(&argc,&argv,MPI_THREAD_FUNNELED,&provided);
    MPI_Comm_rank(MPI_COMM_WORLD,&rank); MPI_Comm_size(MPI_COMM_WORLD,&ranks);
    if(provided<MPI_THREAD_FUNNELED) { MPI_Abort(MPI_COMM_WORLD,2); return 2; }
#endif
    try {
        if(argc==2 && std::string(argv[1])=="--help") {
            if(rank==0) std::cout<<"Options: --n N --d D --k K --seed S --iterations I --tol T --threads T --fixed --details --input FILE --init FILE\n";
#ifdef USE_MPI
            MPI_Finalize();
#endif
            return 0;
        }
        auto end_start=km::Clock::now(); auto o=parse(argc,argv);
#ifdef USE_OMP
        omp_set_dynamic(0); omp_set_num_threads(o.threads);
        int actual=0;
#pragma omp parallel
        {
#pragma omp single
            actual=omp_get_num_threads();
        }
        if(actual!=o.threads) throw std::runtime_error("OpenMP did not provide requested thread count");
#endif
        auto setup_start=km::Clock::now();
        std::vector<int> counts(ranks), offsets(ranks), rowcounts(ranks), rowoffsets(ranks);
        uint64_t cursor=0;
        for(int r=0;r<ranks;++r) {
            uint64_t nr=o.n/ranks+(uint64_t(r)<o.n%ranks);
            rowcounts[r]=int(nr); rowoffsets[r]=int(cursor);
            counts[r]=int(nr*o.d); offsets[r]=int(cursor*o.d); cursor+=nr;
        }
        size_t local_n=rowcounts[rank], begin=rowoffsets[rank], kd=size_t(o.k)*o.d;
        std::vector<double> x(local_n*o.d), centers(kd), full;
        auto ids=km::initial_indices(o.n,o.k,o.seed);
        if(!o.input.empty()) {
            if(rank==0) full=read_values(o.input,size_t(o.n)*o.d);
#ifdef USE_MPI
            MPI_Scatterv(full.data(),counts.data(),offsets.data(),MPI_DOUBLE,x.data(),counts[rank],MPI_DOUBLE,0,MPI_COMM_WORLD);
#else
            x=full;
#endif
        } else {
            for(size_t i=0;i<local_n;++i) for(int j=0;j<o.d;++j)
                x[i*o.d+j]=km::sample(begin+i,j,o.seed);
        }
        if(rank==0) {
            if(!o.init.empty()) centers=read_values(o.init,kd);
            else for(int c=0;c<o.k;++c) for(int j=0;j<o.d;++j)
                centers[size_t(c)*o.d+j]=o.input.empty()?km::sample(ids[c],j,o.seed):full[ids[c]*o.d+j];
        }
#ifdef USE_MPI
        MPI_Bcast(centers.data(),int(kd),MPI_DOUBLE,0,MPI_COMM_WORLD);
#endif
        std::vector<double>().swap(full);
        const auto initial=centers;
        std::vector<double> sums(kd), thread_sums(size_t(o.threads)*kd);
        std::vector<long long> nums(o.k), thread_nums(size_t(o.threads)*o.k);
        std::vector<int> labels(local_n);
        double setup=km::elapsed(setup_start), assignment=0,merge=0,comm=0,update=0;
#ifdef USE_MPI
        MPI_Barrier(MPI_COMM_WORLD);
#endif
        auto loop_start=km::Clock::now(); int iterations=0; double shift=0;
        for(int it=0;it<o.iterations;++it) {
            auto t=km::Clock::now();
            std::fill(thread_sums.begin(),thread_sums.end(),0);
            std::fill(thread_nums.begin(),thread_nums.end(),0);
#ifdef USE_OMP
#pragma omp parallel
#endif
            {
                int tid=0;
#ifdef USE_OMP
                tid=omp_get_thread_num();
#pragma omp for schedule(static)
#endif
                for(size_t i=0;i<local_n;++i) {
                    double dist; int c=km::nearest(&x[i*o.d],centers,o.k,o.d,dist);
                    ++thread_nums[size_t(tid)*o.k+c];
                    for(int j=0;j<o.d;++j) thread_sums[size_t(tid)*kd+size_t(c)*o.d+j]+=x[i*o.d+j];
                }
            }
            assignment+=km::elapsed(t); t=km::Clock::now();
            std::fill(sums.begin(),sums.end(),0); std::fill(nums.begin(),nums.end(),0);
            for(int tid=0;tid<o.threads;++tid) {
                for(size_t q=0;q<kd;++q) sums[q]+=thread_sums[size_t(tid)*kd+q];
                for(int c=0;c<o.k;++c) nums[c]+=thread_nums[size_t(tid)*o.k+c];
            }
            merge+=km::elapsed(t); t=km::Clock::now();
#ifdef USE_MPI
            MPI_Allreduce(MPI_IN_PLACE,sums.data(),int(kd),MPI_DOUBLE,MPI_SUM,MPI_COMM_WORLD);
            MPI_Allreduce(MPI_IN_PLACE,nums.data(),o.k,MPI_LONG_LONG_INT,MPI_SUM,MPI_COMM_WORLD);
            comm+=km::elapsed(t);
#endif
            t=km::Clock::now(); shift=0;
            for(int c=0;c<o.k;++c) {
                double displacement=0;
                if(nums[c]) for(int j=0;j<o.d;++j) {
                    size_t q=size_t(c)*o.d+j; double next=sums[q]/double(nums[c]);
                    double delta=next-centers[q]; displacement+=delta*delta; centers[q]=next;
                }
                shift=std::max(shift,std::sqrt(displacement));
            }
            update+=km::elapsed(t); iterations=it+1;
            if(!o.fixed && shift<=o.tol) break;
        }
        double loop=km::elapsed(loop_start);
        auto final_start=km::Clock::now(); double sse=0;
#ifdef USE_OMP
#pragma omp parallel for reduction(+:sse) schedule(static)
#endif
        for(size_t i=0;i<local_n;++i) {
            double dist; labels[i]=km::nearest(&x[i*o.d],centers,o.k,o.d,dist); sse+=dist;
        }
#ifdef USE_MPI
        MPI_Allreduce(MPI_IN_PLACE,&sse,1,MPI_DOUBLE,MPI_SUM,MPI_COMM_WORLD);
#endif
        double final_time=km::elapsed(final_start), total=km::elapsed(end_start);
        double times[]={setup,assignment,merge,comm,update,loop,final_time,total};
#ifdef USE_MPI
        MPI_Allreduce(MPI_IN_PLACE,times,8,MPI_DOUBLE,MPI_MAX,MPI_COMM_WORLD);
#endif
        std::vector<int> all_labels;
        if(o.details) {
            if(rank==0) all_labels.resize(o.n);
#ifdef USE_MPI
            MPI_Gatherv(labels.data(),int(local_n),MPI_INT,all_labels.data(),rowcounts.data(),rowoffsets.data(),MPI_INT,0,MPI_COMM_WORLD);
#else
            all_labels=labels;
#endif
        }
        if(rank==0) {
            const char* version=
#ifdef USE_OMP
            "hybrid";
#elif defined(USE_MPI)
            "mpi";
#else
            "serial";
#endif
            std::cout<<std::setprecision(17)<<"{\"version\":\""<<version<<"\",\"n\":"<<o.n
                <<",\"d\":"<<o.d<<",\"k\":"<<o.k<<",\"seed\":"<<o.seed
                <<",\"ranks\":"<<ranks<<",\"threads\":"<<o.threads<<",\"iterations\":"<<iterations
                <<",\"fixed\":"<<(o.fixed?"true":"false")<<",\"tolerance\":"<<o.tol
                <<",\"input_kind\":\""<<(o.input.empty()?"synthetic":"file")<<"\",\"sse\":"<<sse
                <<",\"centroid_shift\":"<<shift;
            const char* names[]={"setup_s","assignment_s","merge_s","collectives_s","update_s","loop_s","final_assignment_s","end_to_end_s"};
            for(int i=0;i<8;++i) std::cout<<",\""<<names[i]<<"\":"<<times[i];
            if(o.details) {
                std::cout<<",\"initial_centers\":"; array(std::cout,initial);
                std::cout<<",\"centers\":"; array(std::cout,centers);
                std::cout<<",\"labels\":[";
                for(size_t i=0;i<all_labels.size();++i) {if(i)std::cout<<',';std::cout<<all_labels[i];}std::cout<<']';
            }
            std::cout<<"}\n";
        }
#ifdef USE_MPI
        MPI_Finalize();
#endif
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<"rank "<<rank<<": "<<e.what()<<'\n';
#ifdef USE_MPI
        MPI_Abort(MPI_COMM_WORLD,1);
#endif
        return 1;
    }
}
