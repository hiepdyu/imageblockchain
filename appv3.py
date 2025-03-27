import hashlib
import json
import os
import tempfile
from datetime import datetime
import streamlit as st
from PIL import Image
import cv2
import numpy as np

# ============ BLOCKCHAIN ============
class Block:
    def __init__(self, index, previous_hash, timestamp, data, hash):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data
        self.hash = hash

    @staticmethod
    def calculate_hash(index, previous_hash, timestamp, data):
        return hashlib.sha256(f"{index}{previous_hash}{timestamp}{json.dumps(data)}".encode()).hexdigest()

class Blockchain:
    def __init__(self):
        self.chain = []
        self.create_genesis_block()
    
    def create_genesis_block(self):
        genesis_data = {
            "image_hash": "0", 
            "owner": "Genesis",
            "timestamp": datetime.now().isoformat()
        }
        genesis_block = Block(
            index=0,
            previous_hash="0",
            timestamp=datetime.now().isoformat(),
            data=genesis_data,
            hash=Block.calculate_hash(0, "0", datetime.now().isoformat(), genesis_data)
        )
        self.chain.append(genesis_block)
    
    def add_block(self, data):
        previous_block = self.chain[-1]
        new_block = Block(
            index=previous_block.index + 1,
            previous_hash=previous_block.hash,
            timestamp=datetime.now().isoformat(),
            data=data,
            hash=Block.calculate_hash(
                previous_block.index + 1,
                previous_block.hash,
                datetime.now().isoformat(),
                data
            )
        )
        self.chain.append(new_block)
    
    def save_to_json(self, filename):
        with open(filename, 'w') as f:
            json.dump([block.__dict__ for block in self.chain], f, indent=4)
    
    @classmethod
    def load_from_json(cls, filename):
        instance = cls()
        try:
            with open(filename) as f:
                chain_data = json.load(f)
                instance.chain = [
                    Block(
                        block['index'],
                        block['previous_hash'],
                        block['timestamp'],
                        block['data'],
                        block['hash']
                    ) for block in chain_data
                ]
        except FileNotFoundError:
            pass
        return instance

    def is_valid(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            if current.hash != Block.calculate_hash(
                current.index, current.previous_hash, 
                current.timestamp, current.data
            ):
                return False
            if current.previous_hash != previous.hash:
                return False
        return True

# ============ XỬ LÝ ẢNH ============
def process_image(file):
    img = Image.open(file)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    
    # Resize ảnh max 512px giữ tỉ lệ
    width, height = img.size
    ratio = min(512/width, 512/height)
    new_size = (int(width*ratio), int(height*ratio))
    img = img.resize(new_size, Image.LANCZOS)
    
    # Lưu ảnh đã xử lý
    os.makedirs("uploaded_images", exist_ok=True)
    img_path = f"uploaded_images/{hashlib.sha256(file.getvalue()).hexdigest()}.jpg"
    img.save(img_path, "JPEG", quality=85)
    return img_path

def compare_images(img1_path, img2_path, threshold=0.3):
    try:
        img1 = cv2.imread(img1_path)
        img2 = cv2.imread(img2_path)
        if img1 is None or img2 is None:
            return False
            
        # Chuyển sang ảnh xám và resize
        img1_gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        img2_gray = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        img2_gray = cv2.resize(img2_gray, (img1_gray.shape[1], img1_gray.shape[0]))
        
        # So sánh ảnh
        result = cv2.matchTemplate(img1_gray, img2_gray, cv2.TM_CCOEFF_NORMED)
        similarity = np.max(result)
        return similarity >= threshold
    except:
        return False
    
# ============ XÁC NHẬN BẢN QUYỀN ẢNH ============

# Biến toàn cục để lưu ảnh bản quyền nếu tìm thấy
def get_matched_block():
    if "matched_block" not in st.session_state:
        st.session_state["matched_block"] = None
    return st.session_state["matched_block"]

def is_copyright(file, blockchain):
    # Lưu file tạm
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
        temp_file.write(file.getbuffer())
        temp_path = temp_file.name  # Lấy đường dẫn file tạm
    
    # Băm file ảnh
    img_hash = hashlib.sha256(open(temp_path, "rb").read()).hexdigest()
    
    # Kiểm tra trùng lặp
    duplicate = any(block.data["image_hash"] == img_hash for block in blockchain.chain)
    
    # Kiểm tra ảnh tương tự
    similar = False
    st.session_state["matched_block"] = None
    
    for block in blockchain.chain:
        if "filename" in block.data:
            orig_path = os.path.join("uploaded_images", block.data['filename'])
            if os.path.exists(orig_path) and compare_images(orig_path, temp_path):
                similar = True
                st.session_state["matched_block"] = block
                break
    
    # Xóa ảnh tạm
    os.remove(temp_path)
            
    return duplicate or similar

# ============ GIAO DIỆN ============
def main():
    st.set_page_config("Image Blockchain", layout="wide")
    
    # Khởi tạo
    if 'owner' not in st.session_state:
        st.session_state.owner = ""
    
    # Sidebar
    st.sidebar.title("CHỨC NĂNG")
    tab = st.sidebar.radio(
        "Chọn chức năng",
        ["Đăng ký bản quyền hình ảnh", "Xác minh bản quyền hình ảnh", "Xác minh Blockchain"],
        key="nav"
    )

    blockchain = Blockchain.load_from_json("blockchain.json")

    # Kích thước ảnh hiển thị
    img_with = 400
    
    # TAB ĐĂNG KÝ
    if tab == "Đăng ký bản quyền hình ảnh":
        st.header("Đăng ký ảnh mới")
        
        # Tên chủ sở hữu
        st.session_state.owner = st.text_input("Tên chủ sở hữu", value=st.session_state.owner)
        
        # Upload ảnh mới
        uploaded = st.file_uploader("Tải lên ảnh", type=['png','jpg','jpeg'], key="upload")
        
        if uploaded:
            # Hiển thị ảnh
            st.image(uploaded, width= img_with)
            
            isCopied = is_copyright(uploaded, blockchain)
            
            if isCopied:
                st.error("⚠️ Bạn muốn ăn cắp à? Ảnh đã tồn tại trong hệ thống hoặc ảnh có dấu hiệu chỉnh sửa từ ảnh bản quyền!")
            else:
                if st.button("Xác nhận đăng ký"):
                    img_path = process_image(uploaded)
                    img_hash = hashlib.sha256(open(img_path, "rb").read()).hexdigest()
                    blockchain.add_block({
                        "image_hash": img_hash,
                        "owner": st.session_state.owner,
                        "timestamp": datetime.now().isoformat(),
                        "filename": os.path.basename(img_path)
                    })
                    blockchain.save_to_json("blockchain.json")
                    st.success("✔️ Đăng ký bản quyền thành công!")

    # TAB XÁC MINH
    elif tab == "Xác minh bản quyền hình ảnh":
        st.header("Xác minh bản quyền hình ảnh")
        
        verify_file = st.file_uploader("Tải lên ảnh cần kiểm tra", type=['png','jpg','jpeg'])
        
        if verify_file:
            # Hiển thị ảnh
            st.image(verify_file, width= img_with)
            
            isCopied = is_copyright(verify_file, blockchain)
            
            # Tìm ảnh trùng khớp
            if isCopied:
                st.error("⚠️ Khớp với dữ liệu ảnh bản quyền! Có vẻ bạn tính ăn cắp ảnh này? ")
                matched_block = get_matched_block()
                # Chia thành 2 cột
                col1, col2 = st.columns([2, 2.5]) # Chia tỉ lệ cột

                with col1:
                    st.image(os.path.join("uploaded_images", matched_block.data['filename']), width= img_with, caption="Ảnh gốc đã đăng ký bản quyền")

                with col2:
                    st.write("#### 🔹 Thông tin bản quyền")
                    st.write(f"**📌 Chủ sở hữu:** {matched_block.data['owner']}")
                    st.write(f"**📅 Ngày đăng ký:** {matched_block.data['timestamp']}")
            else:
                st.success("😁 May quá! Ảnh chưa có bản quyền.")
    # TAB BLOCKCHAIN
    else:
        st.header("Xác minh Blockchain")
        if st.button("Kiểm tra tính hợp lệ của Blockchain"):
            if blockchain.is_valid():
                st.success("✅ Blockchain hợp lệ!")
            else:
                st.error("❌ Blockchain không hợp lệ!")

if __name__ == "__main__":
    os.makedirs("uploaded_images", exist_ok=True)
    main()