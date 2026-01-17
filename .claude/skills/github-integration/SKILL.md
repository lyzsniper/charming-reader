---
name: github-integration
description: 集成GitHub MCP工具，支持搜索仓库、查看代码、管理issues和pull requests等GitHub操作
triggers:
  - github
  - git
  - repository
  - repo
  - issue
  - pull request
  - pr
  - commit
  - branch
  - 代码仓库
  - GitHub问题
  - 拉取请求
  - 提交
  - 分支
  - 搜索代码
  - 查看文件
  - 开源项目
  - 查找项目
  - 搜索项目
  - transformer
  - 查找
  - 搜索
version: 1.0.0
---

# GitHub集成技能(GitHub Integration Skill)

## 目标

当用户询问GitHub相关问题或需要执行GitHub操作时，使用此技能通过GitHub MCP工具与GitHub平台交互，实现代码搜索、仓库管理、issue和PR操作等功能。

## 核心能力

本技能提供了完整的GitHub操作能力，包括搜索仓库、查看文件、管理issues和PRs等。

当此技能激活时，GitHub MCP工具会自动动态加载。可用的工具列表取决于MCP服务器的配置，Agent会自动发现并使用这些工具。

## 使用指南

当用户询问GitHub相关问题时，自动激活此技能并加载GitHub MCP工具。

**工具使用原则：**
- 工具列表是动态的，会自动从MCP服务器加载
- Agent应该查看实际可用的工具列表，并使用相应的工具
- 如果某个工具不可用，尝试使用其他类似的工具或方法
- 工具调用失败不应阻塞整个流程，应该优雅地处理错误并继续

## 注意事项

- 所有GitHub操作都需要适当的权限
- 某些操作可能需要仓库的写权限
- 搜索工具支持GitHub的高级搜索语法（如 `language:python`, `topic:machine-learning` 等）
- 工具名称和参数会动态从MCP服务器获取，不需要硬编码
- 如果工具调用失败，应该提供友好的错误信息，而不是阻塞整个流程
