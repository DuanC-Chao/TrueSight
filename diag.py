import sys, pkgutil, pprint
print("sys.path:", *sys.path[:3], "...", sep="\n")
try:
    import backend as P
    print("包路径:", P.__file__)
    print("子模块:", [m.name for m in pkgutil.walk_packages(P.__path__)][:5])
except Exception as e:
    print("导入失败:", e)
