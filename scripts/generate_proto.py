"""
Generate Python code from protobuf definitions
Run this before starting the cluster
"""
import subprocess
import sys
import os

def generate_proto():
    """Generate Python gRPC code from .proto file"""
    proto_dir = os.path.join(os.path.dirname(__file__), '..', 'proto')
    proto_file = os.path.join(proto_dir, 'raft.proto')
    
    if not os.path.exists(proto_file):
        print(f"Error: {proto_file} not found")
        sys.exit(1)
    
    print("Generating gRPC Python code from raft.proto...")
    
    cmd = [
        sys.executable, '-m', 'grpc_tools.protoc',
        f'-I{proto_dir}',
        f'--python_out={proto_dir}',
        f'--grpc_python_out={proto_dir}',
        proto_file
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✓ Generated raft_pb2.py")
        print("✓ Generated raft_pb2_grpc.py")
        print("gRPC code generation successful!")
    else:
        print("Error generating gRPC code:")
        print(result.stderr)
        sys.exit(1)

if __name__ == "__main__":
    generate_proto()
