import sys
import os
sys_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "graph")
sys.path.append(sys_path)
print("sys_path:", sys_path)