class MPQEncryptor:
    def __init__(self, key: str):
        self.key = key.encode('utf-8')  # 将密钥转换为字节
        self.HEADER_SIZE = 3  # MPQ文件头大小改为3字节
        self.MPQ_SIGNATURE = b'MPQ'  # MPQ文件签名
        self.ENCRYPTED_SIGNATURE = b'^$&'  # 加密后的签名

    def encrypt_file(self, file_path: str) -> bool:
        try:
            # 读取文件
            with open(file_path, 'rb') as f:
                data = bytearray(f.read())
            
            # 检查文件大小和签名
            if len(data) < self.HEADER_SIZE:
                print(f"文件太小: {file_path}")
                return False
            
            # 打印前三个字节用于调试
            print(f"文件签名: {data[:3]}")
            
            # 检查是否是MPQ文件（不区分大小写）
            if data[:3].upper() != self.MPQ_SIGNATURE.upper():
                print(f"不是MPQ文件签名: {data[:3]}")
                return False
            
            # 替换签名
            data[:3] = self.ENCRYPTED_SIGNATURE
            
            # 加密数据部分
            key_length = len(self.key)
            for i in range(self.HEADER_SIZE, len(data)):
                data[i] ^= self.key[i % key_length]
            
            # 写回文件
            with open(file_path, 'wb') as f:
                f.write(data)
            
            return True
        except Exception as e:
            print(f"加密文件时出错: {e}")
            return False
            
    def decrypt_file(self, file_path: str) -> bool:
        try:
            # 读取文件
            with open(file_path, 'rb') as f:
                data = bytearray(f.read())
            
            # 检查文件大小和签名
            if len(data) < self.HEADER_SIZE:
                return False
                
            # 检查是否是加密的MPQ文件
            if data[:3] != self.ENCRYPTED_SIGNATURE:
                return False
            
            # 解密数据部分
            key_length = len(self.key)
            for i in range(self.HEADER_SIZE, len(data)):
                data[i] ^= self.key[i % key_length]
            
            # 恢复原始签名
            data[:3] = self.MPQ_SIGNATURE
            
            # 写回文件
            with open(file_path, 'wb') as f:
                f.write(data)
            
            return True
        except Exception as e:
            print(f"解密文件时出错: {e}")
            return False 