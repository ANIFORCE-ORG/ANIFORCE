"""
MCP 服务管理器

职责：
- 在 FastAPI 应用内启动 MCP 服务
- 管理 MCP 服务的生命周期
- 提供服务注册和发现机制
- 支持热更新和调试
"""

import asyncio
from typing import Dict, List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger

from mcp.server.fastmcp import FastMCP
from agents.mcp import MCPServerStreamableHttp, MCPServerManager


class MCPServiceManager:
    """
    MCP 服务管理器
    
    在主应用内管理所有 MCP 服务
    """
    
    def __init__(self):
        self.services: Dict[str, FastMCP] = {}
        self.sdk_servers: Dict[str, MCPServerStreamableHttp] = {}
        self.manager: Optional[MCPServerManager] = None
        self._tasks: List[asyncio.Task] = []
        
    def register_service(self, name: str, service: FastMCP, port: int):
        """
        注册 MCP 服务
        
        Args:
            name: 服务名称
            service: FastMCP 实例
            port: 服务端口
        """
        self.services[name] = service
        logger.info(f"Registered MCP service: {name} on port {port}")
        
    def get_service(self, name: str) -> Optional[FastMCP]:
        """获取 MCP 服务"""
        return self.services.get(name)
    
    async def start_all(self):
        """启动所有注册的 MCP 服务"""
        for name, service in self.services.items():
            # 在后台任务中运行每个 MCP 服务
            task = asyncio.create_task(
                self._run_service(name, service),
                name=f"mcp-service-{name}"
            )
            self._tasks.append(task)
            logger.info(f"Started MCP service: {name}")
        
        # 等待服务启动
        await asyncio.sleep(1)
        
        # 初始化 SDK Manager（用于 Agent 调用）
        await self._init_sdk_manager()
    
    async def _run_service(self, name: str, service: FastMCP):
        """运行单个 MCP 服务"""
        try:
            # FastMCP 的 run 方法会阻塞，我们需要在 task 中运行
            # 注意：这里需要配置服务不阻塞主线程
            logger.info(f"MCP service {name} is running")
            # TODO: 实际运行逻辑需要根据 FastMCP 的 API 调整
        except Exception as e:
            logger.error(f"Error running MCP service {name}: {e}")
    
    async def _init_sdk_manager(self):
        """初始化 SDK Manager（用于 Agent 连接）"""
        servers = []
        
        for name, service in self.services.items():
            # 从 FastMCP 获取配置的端口
            port = service.port
            url = f"http://127.0.0.1:{port}/mcp"
            
            # 创建 SDK 的 MCPServer 实例
            sdk_server = MCPServerStreamableHttp(
                name=name,
                params={"url": url},
                cache_tools_list=True,  # 缓存工具列表
            )
            
            servers.append(sdk_server)
            self.sdk_servers[name] = sdk_server
        
        # 使用 MCPServerManager 管理所有服务
        self.manager = MCPServerManager(
            servers=servers,
            connect_in_parallel=True,
            drop_failed_servers=False,  # 开发阶段保留所有服务
            strict=False,  # 容错模式
        )
        
        await self.manager.__aenter__()
        logger.info(f"Initialized SDK Manager with {len(servers)} MCP services")
    
    async def stop_all(self):
        """停止所有 MCP 服务"""
        # 关闭 SDK Manager
        if self.manager:
            await self.manager.__aexit__(None, None, None)
        
        # 取消所有后台任务
        for task in self._tasks:
            task.cancel()
        
        # 等待任务完成
        await asyncio.gather(*self._tasks, return_exceptions=True)
        
        logger.info("All MCP services stopped")
    
    def get_active_servers(self) -> List[MCPServerStreamableHttp]:
        """
        获取活跃的 MCP 服务列表（供 Agent 使用）
        
        Returns:
            可用的 MCPServerStreamableHttp 列表
        """
        if self.manager:
            return self.manager.active_servers
        return []
    
    def get_service_status(self) -> Dict:
        """获取所有服务状态（用于调试）"""
        status = {
            "registered": list(self.services.keys()),
            "running": [name for name, task in zip(self.services.keys(), self._tasks) if not task.done()],
        }
        
        if self.manager:
            status["active_servers"] = [s.name for s in self.manager.active_servers]
            status["failed_servers"] = [s.name for s in self.manager.failed_servers]
        
        return status


# 全局单例
_mcp_manager: Optional[MCPServiceManager] = None


def get_mcp_manager() -> MCPServiceManager:
    """获取 MCP 管理器单例"""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPServiceManager()
    return _mcp_manager


@asynccontextmanager
async def mcp_lifespan(app: FastAPI):
    """
    FastAPI Lifespan 上下文管理器
    
    用法：
        app = FastAPI(lifespan=mcp_lifespan)
    """
    manager = get_mcp_manager()
    
    # 启动时：启动所有 MCP 服务
    logger.info("Starting MCP services...")
    await manager.start_all()
    
    yield
    
    # 关闭时：停止所有 MCP 服务
    logger.info("Stopping MCP services...")
    await manager.stop_all()
