# Contributing to chatgptmail-2api

感谢你对本项目的关注！

## 开发环境

```bash
# 克隆仓库
git clone https://github.com/keggin-CHN/chatgptmail-2api.git
cd chatgptmail-2api

# 安装依赖
pip install -e ".[dev]"

# 运行测试
python -m pytest tests/ -v

# 或使用 Makefile
make install
make test
```

## 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>(<scope>): <description>

[optional body]
```

类型：
- `feat`: 新功能
- `fix`: 修复
- `docs`: 文档
- `test`: 测试
- `refactor`: 重构
- `chore`: 构建/工具

示例：
```
feat(provider): 新增 xxx 平台支持
fix(boomlify): 修复 XOR 解密边界情况
test(server): 新增 /api/health 集成测试
```

## 添加新 Provider

1. 在 `providers/` 下创建 `xxx.py`
2. 继承 `TempMailClient` 抽象基类
3. 实现 `provider_name`, `generate_email`, `list_emails`, `get_email_detail`
4. 在 `providers/__init__.py` 中注册
5. 在 `server.py` 的 `PROVIDERS` 字典中注册
6. 在 `cli.py` 的 `PROVIDERS` 字典中注册
7. 添加单元测试
8. 更新 README.md 支持平台表格

## 测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行测试并生成覆盖率
python -m pytest tests/ -v --cov=providers --cov-report=term-missing

# 仅运行模拟测试（不需要网络）
python -m pytest tests/test_providers.py tests/test_providers_mock.py -v
```

## License

MIT
