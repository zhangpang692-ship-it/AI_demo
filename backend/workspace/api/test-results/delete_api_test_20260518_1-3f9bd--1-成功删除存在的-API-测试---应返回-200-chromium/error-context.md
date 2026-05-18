# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: delete_api_test_20260518_195631.spec.ts >> DELETE /api/v2/projects/{project_identifier}/api-tests/{api_test_id} - 删除 API 测试 >> 1.1 成功删除存在的 API 测试 - 应返回 200
- Location: tests\delete_api_test_20260518_195631.spec.ts:17:7

# Error details

```
Error: apiRequestContext.delete: getaddrinfo ENOTFOUND api.example.com
Call log:
  - → DELETE https://api.example.com/api/v2/projects/PR-1/api-tests/valid-test-id
    - user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.7778.96 Safari/537.36
    - accept: */*
    - accept-encoding: gzip,deflate,br
    - Authorization: Bearer
    - Content-Type: application/json

```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | // 配置
  4   | const BASE_URL = process.env.API_BASE_URL || 'https://api.example.com';
  5   | const AUTH_TOKEN = process.env.AUTH_TOKEN || '';
  6   | 
  7   | // 默认认证请求头
  8   | const getAuthHeaders = (token?: string) => ({
  9   |   'Authorization': `Bearer ${token || AUTH_TOKEN}`,
  10  |   'Content-Type': 'application/json',
  11  | });
  12  | 
  13  | test.describe('DELETE /api/v2/projects/{project_identifier}/api-tests/{api_test_id} - 删除 API 测试', () => {
  14  | 
  15  |   // ==================== 正常功能测试 ====================
  16  | 
  17  |   test('1.1 成功删除存在的 API 测试 - 应返回 200', async ({ request }) => {
  18  |     // Arrange
  19  |     const projectIdentifier = 'PR-1';
  20  |     const apiTestId = 'valid-test-id';
  21  | 
  22  |     // Act
> 23  |     const response = await request.delete(
      |                                          ^ Error: apiRequestContext.delete: getaddrinfo ENOTFOUND api.example.com
  24  |       `${BASE_URL}/api/v2/projects/${projectIdentifier}/api-tests/${apiTestId}`,
  25  |       {
  26  |         headers: getAuthHeaders(),
  27  |       }
  28  |     );
  29  | 
  30  |     // Assert
  31  |     expect(response.status()).toBe(200);
  32  |     const data = await response.json();
  33  |     // 验证 SuccessResponse schema 结构
  34  |     expect(data).toBeDefined();
  35  |     // 预期响应应包含成功标志
  36  |     expect(typeof data).toBe('object');
  37  |   });
  38  | 
  39  |   // ==================== 异常测试 ====================
  40  | 
  41  |   test('2.1 删除不存在的 API 测试 - 应返回 404 或 422', async ({ request }) => {
  42  |     // Arrange
  43  |     const projectIdentifier = 'PR-1';
  44  |     const nonExistentTestId = 'non-existent-test-id';
  45  | 
  46  |     // Act
  47  |     const response = await request.delete(
  48  |       `${BASE_URL}/api/v2/projects/${projectIdentifier}/api-tests/${nonExistentTestId}`,
  49  |       {
  50  |         headers: getAuthHeaders(),
  51  |       }
  52  |     );
  53  | 
  54  |     // Assert - 资源不存在，应该返回错误状态码
  55  |     expect([404, 422]).toContain(response.status());
  56  |     const error = await response.json().catch(() => ({}));
  57  |     expect(error).toBeDefined();
  58  |   });
  59  | 
  60  |   test('2.2 无效的 project_identifier - 应返回 422', async ({ request }) => {
  61  |     // Arrange
  62  |     const invalidProjectId = 'non-existent-project';
  63  |     const apiTestId = 'test-id-123';
  64  | 
  65  |     // Act
  66  |     const response = await request.delete(
  67  |       `${BASE_URL}/api/v2/projects/${invalidProjectId}/api-tests/${apiTestId}`,
  68  |       {
  69  |         headers: getAuthHeaders(),
  70  |       }
  71  |     );
  72  | 
  73  |     // Assert - 无效的项目标识符应返回验证错误
  74  |     expect(response.status()).toBe(422);
  75  |     const error = await response.json().catch(() => ({}));
  76  |     expect(error).toBeDefined();
  77  |   });
  78  | 
  79  |   test('2.3 空字符串 api_test_id - 应返回 422', async ({ request }) => {
  80  |     // Arrange
  81  |     const projectIdentifier = 'PR-1';
  82  |     const emptyTestId = '';
  83  | 
  84  |     // Act
  85  |     const response = await request.delete(
  86  |       `${BASE_URL}/api/v2/projects/${projectIdentifier}/api-tests/${emptyTestId}`,
  87  |       {
  88  |         headers: getAuthHeaders(),
  89  |       }
  90  |     );
  91  | 
  92  |     // Assert - 空参数应返回验证错误
  93  |     expect(response.status()).toBe(422);
  94  |     const error = await response.json().catch(() => ({}));
  95  |     expect(error).toBeDefined();
  96  |   });
  97  | 
  98  |   // ==================== 边界测试 ====================
  99  | 
  100 |   test('3.1 重复删除同一 API 测试 - 第一次应成功，第二次应返回错误', async ({ request }) => {
  101 |     // Arrange
  102 |     const projectIdentifier = 'PR-1';
  103 |     const apiTestId = 'test-to-delete-twice';
  104 | 
  105 |     // Act - 第一次删除
  106 |     const firstResponse = await request.delete(
  107 |       `${BASE_URL}/api/v2/projects/${projectIdentifier}/api-tests/${apiTestId}`,
  108 |       {
  109 |         headers: getAuthHeaders(),
  110 |       }
  111 |     );
  112 | 
  113 |     // Assert - 第一次删除应成功
  114 |     expect(firstResponse.status()).toBe(200);
  115 | 
  116 |     // Act - 第二次删除（资源已不存在）
  117 |     const secondResponse = await request.delete(
  118 |       `${BASE_URL}/api/v2/projects/${projectIdentifier}/api-tests/${apiTestId}`,
  119 |       {
  120 |         headers: getAuthHeaders(),
  121 |       }
  122 |     );
  123 | 
```