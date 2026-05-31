CXX = g++
CXXFLAGS = -std=c++17 -O2 -Wall -Wextra -fopenmp

TARGET = matmul

SRC = src/main.cpp \
      src/matrix.cpp \
      src/sequential.cpp \
      src/omp_static.cpp \
      src/omp_dynamic.cpp \
      src/omp_optimized.cpp

all: $(TARGET)

$(TARGET): $(SRC)
	$(CXX) $(CXXFLAGS) $(SRC) -o $(TARGET)

clean:
	rm -rf $(TARGET) *.o plots
