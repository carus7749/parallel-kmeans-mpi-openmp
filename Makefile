CXX = c++
MPICXX ?= mpicxx
CXXFLAGS ?= -O3 -std=c++17 -Wall -Wextra -Wpedantic
OMPFLAGS ?= -fopenmp
CPPFLAGS ?=
LDLIBS ?=

all: bin/kmeans_serial bin/kmeans_mpi bin/kmeans_hybrid
bin:
	mkdir -p bin
bin/kmeans_serial: src/main.cpp include/kmeans.hpp | bin
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -Iinclude $< -o $@ $(LDLIBS)
bin/kmeans_mpi: src/main.cpp include/kmeans.hpp | bin
	$(MPICXX) $(CPPFLAGS) $(CXXFLAGS) -DUSE_MPI -Iinclude $< -o $@ $(LDLIBS)
bin/kmeans_hybrid: src/main.cpp include/kmeans.hpp | bin
	$(MPICXX) $(CPPFLAGS) $(CXXFLAGS) $(OMPFLAGS) -DUSE_MPI -DUSE_OMP -Iinclude $< -o $@ $(LDLIBS)
test: all
	python3 tests/test_correctness.py
clean:
	rm -rf bin
.PHONY: all test clean
