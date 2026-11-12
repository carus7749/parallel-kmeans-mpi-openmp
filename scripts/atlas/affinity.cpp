// Linux-only preflight: verify each OpenMP thread is pinned to a distinct
// physical core across all MPI ranks in this single-node allocation.
#include <mpi.h>
#include <omp.h>
#include <sched.h>
#include <fstream>
#include <iostream>
#include <set>
#include <string>
#include <vector>
int read_id(int cpu,const char* field) {
    int v=-1; std::ifstream f("/sys/devices/system/cpu/cpu"+std::to_string(cpu)+"/topology/"+field);
    f>>v;return v;
}
int main(int argc,char** argv) {
    int provided,rank,size;MPI_Init_thread(&argc,&argv,MPI_THREAD_FUNNELED,&provided);
    MPI_Comm_rank(MPI_COMM_WORLD,&rank);MPI_Comm_size(MPI_COMM_WORLD,&size);
    int t=1;for(int i=1;i+1<argc;++i) if(std::string(argv[i])=="--threads") t=std::stoi(argv[i+1]);
    if(t<1 || provided<MPI_THREAD_FUNNELED) MPI_Abort(MPI_COMM_WORLD,2);
    omp_set_dynamic(0);omp_set_num_threads(t);
    std::vector<int> pairs(2*t,-1);int bad=0;
#pragma omp parallel reduction(|:bad)
    {
        int id=omp_get_thread_num();cpu_set_t mask;CPU_ZERO(&mask);
        if(omp_get_num_threads()!=t || sched_getaffinity(0,sizeof(mask),&mask)!=0) bad=1;
        std::set<std::pair<int,int>> physical;
        for(int cpu=0;cpu<CPU_SETSIZE;++cpu) if(CPU_ISSET(cpu,&mask))
            physical.insert({read_id(cpu,"physical_package_id"),read_id(cpu,"core_id")});
        if(physical.size()!=1) bad=1;
        else {
            auto q=*physical.begin();pairs[2*id]=q.first;pairs[2*id+1]=q.second;
            if(q.first<0||q.second<0)bad=1;
        }
    }
    std::vector<int> all(2*t*size);
    MPI_Allgather(pairs.data(),2*t,MPI_INT,all.data(),2*t,MPI_INT,MPI_COMM_WORLD);
    std::set<std::pair<int,int>> unique;
    for(int i=0;i<size*t;++i)unique.insert({all[2*i],all[2*i+1]});
    if(int(unique.size())!=size*t)bad=1;
    MPI_Allreduce(MPI_IN_PLACE,&bad,1,MPI_INT,MPI_MAX,MPI_COMM_WORLD);
    if(rank==0) {
        for(int i=0;i<size*t;++i)std::cout<<"rank="<<i/t<<" thread="<<i%t<<" socket="<<all[2*i]<<" core="<<all[2*i+1]<<'\n';
        std::cout<<(bad?"FAIL":"PASS")<<" physical-core affinity\n";
    }
    MPI_Finalize();return bad?1:0;
}
