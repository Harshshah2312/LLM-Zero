FROM public.ecr.aws/sam/build-python3.12:latest
RUN dnf install -y \
    gcc-c++ \
    make \
    cmake \
    openblas-devel \
    git \
    gcc-gfortran
WORKDIR /build
RUN git clone https://github.com/abetlen/llama-cpp-python.git && \
    cd llama-cpp-python && \
    git checkout v0.3.7 && \
    git submodule update --init --recursive
WORKDIR /build/llama-cpp-python
ENV CMAKE_ARGS="-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS -DGGML_NATIVE=OFF -DGGML_LTO=ON -DGGML_AVX2=ON -DGGML_AVX512=OFF"
ENV LLAMA_BLAS=1
ENV LLAMA_OPENBLAS=1
ENV LLAMA_METAL=0
ENV LLAMA_CUDA=0
RUN python -m pip install build && python -m build --wheel
RUN mkdir -p /opt/python/ && \
    pip install dist/*.whl -t /opt/python/ && \
    mkdir -p /opt/lib && \
    cp /usr/lib64/libopenblas.so.0 /opt/lib/ && \
    cp /usr/lib64/libgfortran.so.5 /opt/lib/ && \
    cp /usr/lib64/libquadmath.so.0 /opt/lib/ && \
    cp /usr/lib64/libgomp.so.1 /opt/lib/