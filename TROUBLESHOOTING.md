# 问题诊断与解决方案

## 问题描述

当使用 FastAPI 封装 Playwright 同步 API 时，出现以下错误：
```
It looks like you are using Playwright Sync API inside the asyncio loop.
Please use the Async API instead.
```

## 根本原因

FastAPI 是一个异步框架，所有的请求处理函数都在 asyncio 事件循环中运行。Playwright 的同步 API（`sync_playwright`）检测到 asyncio 事件循环时会拒绝运行，即使使用 `run_in_executor` 也无法绕过这个限制。

## 解决方案

将 Playwright 同步 API 改为异步 API（`async_playwright`），创建新文件 `jplatpat_scraper_async.py`。

### 主要修改点

1. **导入改变**
   ```python
   # 从
   from playwright.sync_api import sync_playwright
   # 改为
   from playwright.async_api import async_playwright
   ```

2. **所有函数改为异步**
   ```python
   # 所有辅助函数都需要改为 async
   async def _clean_text(element) -> str:
       text = (await element.inner_text()).strip()  # 需要 await
       return " ".join(text.split())
   ```

3. **所有 Playwright 调用都需要 await**
   - `page.goto()` → `await page.goto()`
   - `page.query_selector()` → `await page.query_selector()`
   - `element.inner_text()` → `await element.inner_text()`
   - `page.click()` → `await page.click()`
   - 等等...

4. **列表推导式需要改为循环**
   ```python
   # 不能这样写（列表推导式中无法使用 await）
   status = " / ".join([await _clean_text(label) for label in status_labels])
   
   # 需要改为
   status_parts = []
   for label in status_labels:
       clean = await _clean_text(label)
       if clean:
           status_parts.append(clean)
   status = " / ".join(status_parts)
   ```

## 测试结果

✅ API 服务正常启动  
✅ 健康检查端点工作正常  
✅ 搜索功能正常  
✅ 可以正确提取专利信息  

## 使用方法

```bash
# 启动 API
python api.py

# 测试搜索
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "量子コンピュータ", "limit": 2, "fetch_abstract": false}'
```

## 注意事项

- 命令行版本 `jplatpat_scraper.py` 仍然使用同步 API，保持向后兼容
- FastAPI 版本使用新的异步模块 `jplatpat_scraper_async.py`
- 两个版本功能完全一致，只是 API 风格不同
