"""验证 gatewayaivectormemory 模块能正常导入"""
import sys
sys.path.insert(0, ".")

try:
    import gatewayaivectormemory
    print(f"✓ import gatewayaivectormemory OK, version={gatewayaivectormemory.__version__}")
except Exception as e:
    print(f"✗ import gatewayaivectormemory FAILED: {e}")
    sys.exit(1)

try:
    from gatewayaivectormemory.server import MCPServer
    print("✓ from gatewayaivectormemory.server import MCPServer OK")
except Exception as e:
    print(f"✗ server import FAILED: {e}")
    sys.exit(1)

try:
    from gatewayaivectormemory.install import RUNNERS, IDES
    print(f"✓ install.py OK, {len(RUNNERS)} runners, {len(IDES)} IDEs")
except Exception as e:
    print(f"✗ install import FAILED: {e}")
    sys.exit(1)

try:
    from gatewayaivectormemory.web.app import run_web
    print("✓ web.app import OK")
except Exception as e:
    print(f"✗ web.app import FAILED: {e}")
    sys.exit(1)

print("\n全部导入测试通过")
