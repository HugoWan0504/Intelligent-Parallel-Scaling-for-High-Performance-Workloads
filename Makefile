CXX = g++
CXXFLAGS = -std=c++17 -O2 -Wall -Wextra -fopenmp

TARGET = matmul

SRC = src/main.cpp \
      src/matrix.cpp \
      src/sequential.cpp \
      src/pthread_static.cpp \
      src/pthread_dynamic.cpp \
      src/pthread_optimized.cpp

all: $(TARGET)

$(TARGET): $(SRC)
	$(CXX) $(CXXFLAGS) $(SRC) -o $(TARGET)

clean:
	rm -rf $(TARGET) *.o plots
