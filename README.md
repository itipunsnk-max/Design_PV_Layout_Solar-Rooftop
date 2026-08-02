# Solar Rooftop String & MPPT Design Assistant

เครื่องมือ Streamlit สำหรับช่วยออกแบบเบื้องต้นของ Solar Rooftop ได้แก่ String, MPPT, การแบ่งชุด Inverter, สาย DC, QA/QC และข้อมูลเตรียมสำหรับ PVsyst

## ความสามารถหลัก

- เลือก Inverter และจำนวน Inverter แบบ `AUTO` หรือกำหนดเอง
- ตรวจ String voltage/current และจัด String ลง physical Inverter, MPPT และ input
- หากจำนวน String ทำให้กระแสรวมของ MPPT เกินข้อจำกัด ระบบจะแสดง `WARNING` พร้อมระบุ Inverter/MPPT ที่เกี่ยวข้อง
- เมื่อเลือกจำนวน Inverter เป็น `AUTO` ระบบจะลองเพิ่มจำนวนเครื่องจนกว่าจะจัดได้โดยไม่มี MPPT current warning; เช่น 14 String กับ SG125CX-P2 จะขยับจาก 1 เป็น 2 เครื่องเมื่อ 1 เครื่องไม่พอ
- หากผู้ใช้กำหนด Inverter 1 เครื่อง หรือกำหนด String เป็น `INV01` ทั้งหมด ระบบจะแสดงการจัดจริงไว้เพื่อให้ตรวจสอบ พร้อมคงสถานะ `WARNING` ไว้ ไม่ซ่อนปัญหา
- ตารางผลการจัด String และตาราง Export บนหน้า 1 จะไฮไลท์สีแดงทั้งแถวของ String ที่อยู่ใน MPPT ซึ่งมีปัญหา เพื่อให้เห็นกลุ่ม String ที่ต้องแก้ไข
- ตารางกรอกข้อมูลมีคอลัมน์ท้าย `MPPT (AUTO/ระบุ)` และ `String (AUTO/ระบุ)` รองรับ `AUTO` หรือหมายเลขช่อง
- Paste จาก Excel รองรับรูปแบบเดิมและรูปแบบใหม่ที่เติม MPPT/String override ต่อท้าย

## โครงสร้างไฟล์

- `calculation_engine.py` — Calculation Engine แบบไม่พึ่ง Streamlit: master data, สูตรไฟฟ้า, String/MPPT assignment, สาย DC, QA/QC และ PVsyst preparation
- `streamlit_app.py` — UI ภาษาไทย, Session State, ตารางกรอก/ผลลัพธ์, สี Warning/Highlight และ Export
- `STREAMLIT_FLOW.md` — Flow การทำงาน, ลำดับการคำนวณ, เงื่อนไข AUTO และสูตรหลัก
- `PROGRAM_GUIDE.md` — คู่มือการใช้งาน, โครงสร้างข้อมูล, Config และรูปแบบ Paste/Export
- `test_calculation_engine.py` — Unit tests ของ Calculation Engine และกรณี 14 String ที่กระแส MPPT เกิน

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

## ตรวจสอบก่อนใช้งาน

```bash
python -m py_compile streamlit_app.py calculation_engine.py test_calculation_engine.py
python -m pytest -q
```

ผลลัพธ์เป็นเครื่องมือช่วยออกแบบเบื้องต้น ต้องยืนยันกับ datasheet ล่าสุดของผู้ผลิต, PAN/OND, PVsyst, ข้อมูลหน้างาน, มาตรฐาน/ข้อกำหนดการไฟฟ้า และวิศวกรผู้มีใบอนุญาตก่อนนำไปออกแบบหรือก่อสร้างจริง
