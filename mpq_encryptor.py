class MPQEncryptor:
    def __init__(self, key: str):
        self.ENCRYPT_SIZE = 512  # 只加密前512字节
        self.HEADER_SIZE = 3     # MPQ文件头大小为3字节
        self.MPQ_SIGNATURE = b'MPQ'  # MPQ文件签名
        self.ENCRYPTED_SIGNATURE = b'^$&'  # 加密后的签名
        self.KEY = key.encode('utf-8')  # 使用传入的通信密钥

    def encrypt_file(self, file_path: str) -> bool:
        try:
            # 读取文件
            with open(file_path, 'rb') as f:
                data = bytearray(f.read())
            
            # 检查文件大小和签名
            if len(data) < self.HEADER_SIZE:
                print(f"文件太小: {file_path}")
                return False
            
            # 只在文件是MPQ文件时进行加密
            if data[:3] == self.MPQ_SIGNATURE:
                # 替换签名
                data[:3] = self.ENCRYPTED_SIGNATURE
                
                # 只加密指定大小的数据
                encrypt_length = min(self.ENCRYPT_SIZE, len(data))
                key_length = len(self.KEY)
                
                # 从文件头之后开始加密
                for i in range(self.HEADER_SIZE, encrypt_length):
                    data[i] ^= self.KEY[i % key_length]
                
                # 写回文件
                with open(file_path, 'wb') as f:
                    f.write(data)
                return True
            
            return False
            
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
                
            # 只在文件是加密的MPQ文件时进行解密
            if data[:3] == self.ENCRYPTED_SIGNATURE:
                # 解密指定大小的数据
                decrypt_length = min(self.ENCRYPT_SIZE, len(data))
                key_length = len(self.KEY)
                
                # 从文件头之后开始解密
                for i in range(self.HEADER_SIZE, decrypt_length):
                    data[i] ^= self.KEY[i % key_length]
                
                # 恢复原始签名
                data[:3] = self.MPQ_SIGNATURE
                
                # 写回文件
                with open(file_path, 'wb') as f:
                    f.write(data)
                return True
            
            return False
            
        except Exception as e:
            print(f"解密文件时出错: {e}")
            return False 