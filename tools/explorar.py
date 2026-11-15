import runpy, sys
sys.argv = ["x"]
m = runpy.run_path("scripts/prefeitura_indices.py")
print(m["balanco"]())
