import sys
import os
sys_path = os.path.join(os.path.dirname(os.path.abspath(__file__)))
# 添加所有第三库的调用到这个文件
thirdparty_path = os.path.join(sys_path, "thirdparty")
sys.path.append(thirdparty_path)
sys.path.append(sys_path)
print("sys_path:", sys_path)
