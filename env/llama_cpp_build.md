# llama.cpp build record

状态：`PASS（CPU host build）`。

## Source lock

- Repository: `https://github.com/ggml-org/llama.cpp.git`
- Commit: `7ab4ee7baad2d920464cbacfad4f4b07cf111fd2`
- Reported source version: `0.4.1-dev`
- ggml version: `0.24.0`
- Build directory: `runtime/llama.cpp/build/`

## Build command

```bash
source env/setup_host_tools.sh
cmake -S runtime/llama.cpp -B runtime/llama.cpp/build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build runtime/llama.cpp/build -j$(nproc)
```

结果：Ninja `428/428` 完成，CPU/OpenMP/OpenSSL backend 配置通过。

## Smoke checks

```text
runtime/llama.cpp/build/bin/llama-cli --help      PASS
runtime/llama.cpp/build/bin/llama-server --help   PASS
runtime/llama.cpp/build/bin/llama-mtmd-cli --help PASS
```

当前 commit 的实际产物名称为 `llama-cli`、`llama-server`、`llama-mtmd-cli`；没有假定旧教程中的 binary 名称。

## Binary SHA256

```text
1512e9a6f74abfc760a80f752a46d4a135e96c158d898861814394d43eeb2f5a  llama-cli
3dbb9d6ec1feb2e519e0295a96c9480b07829d6ac683a3e05910b8eac3fbf7  llama-server
17f33b3915301aa575af9e972cbe3bf7d34a7a96e52599918500d148f1f54312  llama-mtmd-cli
```

注：构建过程中 UI asset 从 llama.cpp 的官方构建逻辑下载并嵌入；未下载或转换模型。
