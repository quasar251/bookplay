"""快速验证 Agent 框架是否可用"""

from agents import Registry, ExtractAgent


def test_registry():
    reg = Registry()
    
    # 检查自动注册的 Agent
    agents = reg.list_agents()
    print(f"OK: {len(agents)} agent(s) registered")
    for agent in agents:
        print(f"  - {agent['name']}: {agent['description']}")
    
    # 检查注册/注销功能
    assert reg.has("extract"), "ExtractAgent should be registered"
    
    # 检查重复注册保护
    try:
        extract2 = ExtractAgent()
        reg.register(extract2)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"Dup registration blocked: {e}")
    
    # 注销然后重新注册
    assert reg.unregister("extract") is True
    assert reg.has("extract") is False
    
    new_extract = ExtractAgent()
    reg.register(new_extract)
    assert reg.has("extract") is True
    print("Register/unregister cycle OK")
    
    print("\nAll tests passed!")


if __name__ == "__main__":
    test_registry()
