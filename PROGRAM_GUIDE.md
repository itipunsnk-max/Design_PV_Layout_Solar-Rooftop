# คู่มือโครงสร้างโปรแกรม Solar Rooftop String & MPPT Design Assistant

## 1. วัตถุประสงค์

โปรแกรมนี้ใช้ช่วยออกแบบเบื้องต้นสำหรับระบบ Solar Rooftop โดยรับข้อมูลแผงบนหลังคา
ตรวจช่วงแรงดันของ String จัด String ลง Inverter/MPPT คำนวณสาย DC ตรวจ QA/QC
และเตรียมข้อมูลสำหรับนำไปตรวจต่อใน PVsyst

> โปรแกรมเป็นเครื่องมือช่วยออกแบบ ไม่แทน datasheet ฉบับล่าสุด การตรวจหน้างาน
> มาตรฐานที่เกี่ยวข้อง หรือการรับรองโดยวิศวกรผู้มีใบอนุญาต

## 2. โครงสร้างไฟล์

| ไฟล์ | หน้าที่ |
|---|---|
| `streamlit_app.py` | หน้าจอ Streamlit, รับค่า, แสดงตาราง/สถานะ และสร้างไฟล์ดาวน์โหลด |
| `calculation_engine.py` | Calculation Engine ที่ไม่มี Streamlit: master data, สูตรไฟฟ้า, การจัด MPPT, สาย DC, QA/QC และ PVsyst export |
| `test_calculation_engine.py` | Unit tests สำหรับค่าตั้งต้น 725 W, การคำนวณ String, แถวว่าง และการแบ่งโหลดราย Inverter |
| `requirements.txt` | Python packages ที่โปรแกรมต้องใช้ |
| `Spec. อุปกรณ์/` | Datasheet อ้างอิงของแผงและ Inverter |
| `README.md` | วิธีติดตั้งและเริ่มโปรแกรมฉบับย่อ |

ลำดับการทำงานหลัก:

```text
Master Data + Design Basis + Roof Groups
                  |
                  v
       ตรวจขนาดและแรงดัน String
                  |
                  v
       กระจาย String ไปแต่ละ INVxx
                  |
                  v
        จัด MPPT ภายใน Inverter
                  |
                  v
       คำนวณสาย DC + QA/QC
                  |
                  v
       ตารางหน้าจอ + CSV/JSON/PVsyst
```

## 3. ค่าแผงเริ่มต้น 725 W

ค่าเริ่มต้นอยู่ใน `DEFAULT_MODULES` ของ `calculation_engine.py`

| รายการ | ค่าเริ่มต้น |
|---|---:|
| Module ID | `JINKO-725-BDV` |
| Model | `JKM725N-66HL5-BDV-Z2C2-OC` |
| Pmax | 725 W |
| Vmp | 41.00 V |
| Imp | 17.69 A |
| Voc | 49.20 V |
| Isc | 18.74 A |
| Module efficiency | 23.35% |
| Power measurement tolerance | ±3% |
| Power sorting | 0 ถึง +3 W |
| Temperature coefficient of Pmax | -0.29%/°C |
| Temperature coefficient of Voc | -0.25%/°C |
| Temperature coefficient of Isc | +0.045%/°C |

ค่า `beta_vmp_pct_c` ใช้ค่า -0.29%/°C เป็นค่าเริ่มต้นของ Calculation Engine
เพื่อคำนวณ Vmp ที่อุณหภูมิเซลล์สูง ต้องยืนยันค่านี้กับข้อมูลวิศวกรรมที่อนุมัติก่อนออกแบบจริง

## 4. จุดที่แก้ไขเพื่อ Config

### 4.1 Master data แบบถาวร

แก้ใน `calculation_engine.py`

- `DEFAULT_MODULES`: เพิ่มหรือแก้รุ่นแผง, Pmax, Vmp, Imp, Voc, Isc และ temperature coefficients
- `DEFAULT_INVERTERS`: เพิ่มหรือแก้ช่วงแรงดัน, กระแสต่อ MPPT, จำนวน MPPT,
  จำนวน input ต่อ MPPT และกำลัง AC

ชื่อ field สำคัญของแผง:

| Field | ความหมาย | หน่วย |
|---|---|---|
| `pmax_w` | กำลังสูงสุดของแผง | W |
| `vmp_v`, `imp_a` | แรงดัน/กระแสที่ Maximum Power Point | V, A |
| `voc_v`, `isc_a` | แรงดันวงจรเปิด/กระแสลัดวงจร | V, A |
| `beta_voc_pct_c` | Temperature coefficient ของ Voc | %/°C |
| `beta_vmp_pct_c` | Temperature coefficient ที่ใช้กับ Vmp | %/°C |
| `max_system_v` | แรงดันระบบสูงสุดของแผง | V |
| `fuse_a` | Maximum series fuse rating | A |

ชื่อ field สำคัญของ Inverter:

| Field | ความหมาย |
|---|---|
| `dc_max_v` | แรงดัน DC สูงสุด |
| `startup_v` | แรงดันเริ่มทำงาน |
| `mppt_min_v`, `mppt_max_v` | ช่วงแรงดัน MPPT |
| `max_i_mppt_a` | กระแสใช้งานสูงสุดต่อ MPPT |
| `max_isc_mppt_a` | กระแสลัดวงจรสูงสุดต่อ MPPT |
| `max_i_input_a` | กระแสสูงสุดต่อ DC input |
| `mppt_qty` | จำนวน MPPT ต่อเครื่อง |
| `inputs_per_mppt` | จำนวน DC input ต่อ MPPT |
| `rated_ac_kw` | กำลัง AC พิกัดต่อเครื่อง |

### 4.2 Config จากหน้าจอโดยไม่แก้โค้ด

แท็บ **1. ข้อมูลตั้งต้น**

- เลือกรุ่นแผงและ Inverter
- ปรับกำลังแผงสำหรับกรณีศึกษา
- กำหนดจำนวน Inverter
- กำหนด Tmin, Tcell,max และ voltage safety factor
- กำหนด DC/AC ratio สูงสุด
- เลือกวัสดุ/ขนาดสาย และเกณฑ์ voltage drop/DC loss
- กรอก Candidate strings จาก roof layout

แท็บ **Master Data**

- แก้ข้อมูล datasheet ระหว่าง session ได้
- ต้องแก้ `verification_status` และ `source` ให้สอดคล้องกับ datasheet
- การแก้จากหน้าจอไม่ใช่การแก้ค่า default ถาวรใน source code

### 4.3 Roof layout / Candidate strings

หนึ่งแถวหมายถึงหนึ่ง Candidate string group:

| Field | ความหมาย |
|---|---|
| `roof_id`, `zone`, `group_id` | ตำแหน่งอ้างอิงบนหลังคา |
| `modules` | จำนวนแผงอนุกรมใน String |
| `orientation` | แนววางแผง |
| `tilt_deg`, `azimuth_deg` | มุมเอียงและทิศ |
| `shading` | กลุ่มสภาพเงา |
| `one_way_m` | ระยะสายจริงขาเดียวจาก String ถึงจุดเชื่อมต่อ |

ตารางจะแสดงคอลัมน์คำนวณอัตโนมัติถัดจากจำนวนแผง:

- `กำลัง DC (kWp)` = จำนวนแผง × กำลังแผง ÷ 1,000
- `Inverter Set` = ชุด Inverter ที่โปรแกรมจัดให้ เช่น `INV01`, `INV02`
- `UNASSIGNED` = ยังไม่มี MPPT/Input ที่รองรับ String นั้นได้

ค่า `kWp` ทุกตารางและ Summary แสดงผลด้วยทศนิยม 3 ตำแหน่ง
โดยไม่มีการปัดค่าที่ใช้ใน Calculation Engine

คอลัมน์ `Inverter Set` ใช้สีแยกตามชุด เช่น INV01 สีฟ้า, INV02 สีเขียว,
INV03 สีเหลือง และใช้สีเดียวกับการ์ดสรุปเหนือ Candidate strings
การ์ดแต่ละใบแสดงจำนวน Strings, จำนวนแผง และ DC kWp ของ Inverter ชุดนั้น

คอลัมน์ `เลือก Inverter` รองรับ:

- `AUTO` ให้โปรแกรมแบ่ง String เป็นกลุ่มต่อเนื่องตามจำนวน Inverter
- `INV01`, `INV02`, ... บังคับ String แถวนั้นไปยังเครื่องที่เลือก
- `Assigned Inverter` แสดงเครื่องที่จัดได้จริง
- การเลือกด้วยผู้ใช้เป็น hard constraint; หาก MPPT/Input ของเครื่องนั้นเต็มหรือ
  ไม่เข้ากัน ระบบแสดง `UNASSIGNED/FAIL` และจะไม่ย้ายไปเครื่องอื่นอัตโนมัติ

เหนือ Candidate strings จะแสดง Total modules, Total DC kWp, จำนวน Inverter
และ Project DC/AC ratio โดยอัตโนมัติ

String ที่ต่อขนานบน MPPT เดียวกันต้องมีจำนวนแผง, orientation และ shading เหมือนกัน

### 4.4 การแก้ค่าบนตารางหลังเปลี่ยน Inverter

- เมื่อเปลี่ยนรุ่น, กำลังแผง หรือจำนวน Inverter ตารางจะสร้าง design state ใหม่
  และคำนวณ `กำลัง DC (kWp)`/`Inverter Set` ใหม่อัตโนมัติ
- คอลัมน์ข้อมูลหน้างาน เช่น จำนวนแผง, Orientation และ One-way cable
  ยังคงแก้ไขได้ตามปกติ
- `กำลัง DC (kWp)` และ `Inverter Set` เป็นผลคำนวณจึงตั้งใจให้เป็น read-only
- โปรแกรมเก็บตารางฉบับเต็มหลังแก้ทุกครั้ง จึงรองรับการกรอกต่อเนื่อง,
  copy/paste หลายช่อง และเพิ่ม/ลบแถวโดยไม่ย้อนกลับไปใช้ snapshot เก่า
- หลังกรอกหรือ Paste จาก Excel ต้องกด **บันทึกข้อมูลและคำนวณใหม่**
  เพื่อ Commit ตารางทั้งชุด แล้วโปรแกรมจึงเติม kWp/Inverter Set
- รองรับลำดับคอลัมน์ Excel เดิม:
  `roof_id, zone, group_id, modules, string_kwp, inverter_id, orientation,
  tilt_deg, azimuth_deg, shading, one_way_m`
  โดยค่า `string_kwp` จาก Excel จะถูกคำนวณใหม่ และ `Assigned Inverter`
  จะแสดงหลัง Submit
- เมื่อต้อง Paste หลายแถว ให้ใช้ส่วน **Paste หลายแถวจาก Excel** ซึ่งรองรับ
  รูปแบบ 10 คอลัมน์ (input only), 11 คอลัมน์ (legacy) และ 12 คอลัมน์
  (มี Assigned Inverter) พร้อมเลือกเพิ่มต่อท้ายหรือแทนที่ทั้งหมด
- ตารางกรอกหลักคงลำดับ 11 คอลัมน์ให้ตรงกับ Excel เดิม และแยก
  `Assigned Inverter` ไปแสดงในตารางผลการจัด Inverter ราย String ด้านล่าง
  เพื่อไม่ให้คอลัมน์จาก Excel เลื่อนหรือสูญหายขณะ Paste
- One-way cable เป็น Optional ในขั้น String design; หากเว้นว่าง ระบบยังคำนวณ
  kWp/MPPT ได้ แต่ส่วนตรวจสายจะแสดง Warning จนกว่าจะกรอกระยะ
- หาก Streamlit Cloud เพิ่ง deploy source code รุ่นใหม่ ให้ Reload หน้าเพื่อล้าง widget
  state จาก source code รุ่นก่อนหนึ่งครั้ง

## 5. การแบ่ง Design เป็นราย Inverter

Calculation Engine สร้างรหัสเครื่องเป็น `INV01`, `INV02`, ... ตามจำนวน Inverter ที่เลือก
และทำงานตามลำดับนี้:

1. ตรวจว่าแต่ละ Candidate string ผ่านช่วงแรงดันและกระแส
2. หา MPPT slot ที่จำนวนแผง, orientation และ shading เข้ากัน
3. แบ่งแถวตามลำดับเป็นกลุ่มต่อเนื่องและใกล้เคียงกัน เช่น
   `G01-G12 = INV01`, `G13-G23 = INV02`
4. ภายใน Inverter ของกลุ่มนั้น เลือก MPPT ที่มีจำนวน input ใช้น้อยที่สุด
5. ตรวจ `inputs_per_mppt`, `max_i_mppt_a` และ `max_isc_mppt_a`
6. ถ้าชุดที่กำหนดไม่มี slot ที่ผ่าน โปรแกรมจะลอง Inverter ชุดอื่นก่อน
7. ถ้าไม่มี slot ที่ผ่านทุกชุด จะกำหนดเป็น `UNASSIGNED` และสถานะ `FAIL`

ผลลัพธ์ `inverter_summary` แสดงรายเครื่อง:

- จำนวน String และแผงที่จัดเข้า
- กำลัง DC ที่จัดเข้าและกำลัง AC พิกัด
- DC/AC ratio รายเครื่อง
- จำนวน MPPT และ input ที่ใช้
- สถานะ `PASS`, `WARNING` หรือ `FAIL`

หน้าจอ **3. MPPT & Cable** แสดงตารางสรุปทุกเครื่องและแยกแท็บตาม `INVxx`
ส่วน JSON export เก็บทั้ง `inverter_sets` และ `assignments`

## 6. โครงสร้างสูตร

### 6.1 แรงดันแผงเมื่ออากาศเย็น

```text
Voc_cold = Voc_STC × [1 + |βVoc| × (25 - Tmin)]
```

โดย temperature coefficient ในสูตรต้องแปลงจาก `%/°C` เป็น `1/°C`

### 6.2 แรงดันทำงานเมื่อเซลล์ร้อน

```text
Vmp_hot = Vmp_STC × [1 + βVmp × (Tcell,max - 25)]
```

### 6.3 จำนวนแผงสูงสุดต่อ String

ขีดจำกัด absolute:

```text
Nmax_absolute = FLOOR(Inverter DC max voltage / Voc_cold)
```

ขีดจำกัดสำหรับออกแบบที่มี margin:

```text
Nmax_design =
    FLOOR(Inverter DC max voltage × voltage safety factor / Voc_cold)
```

### 6.4 จำนวนแผงต่ำสุดต่อ String

```text
Nmin_MPPT = CEILING(Inverter MPPT min voltage / Vmp_hot)
```

Candidate string ผ่านเมื่อ:

```text
Nmin_MPPT <= modules <= Nmax_design
String Vmp_hot >= startup voltage
MPPT min voltage <= String Vmp_hot <= MPPT max voltage
String Voc_cold <= Inverter DC max voltage
Module Imp <= max current per input
```

### 6.5 กระแสของ MPPT เมื่อขนานหลาย String

```text
Imp_MPPT = จำนวน String ขนาน × Imp_module
Isc_MPPT = จำนวน String ขนาน × Isc_module
```

ต้องผ่านทั้ง:

```text
Imp_MPPT <= max_i_mppt_a
Isc_MPPT <= max_isc_mppt_a
จำนวน String ขนาน <= inputs_per_mppt
```

### 6.6 DC/AC ratio

ระดับโครงการ:

```text
DC/AC ratio = Total installed DC kWp
               / (Rated AC kW ต่อเครื่อง × จำนวน Inverter)
```

ระดับ Inverter:

```text
DC/AC ratio ของ INVxx = Assigned DC kWp / Rated AC kW ของเครื่อง
```

### 6.7 ความต้านทานและการสูญเสียสาย DC

```text
Loop length = 2 × One-way cable length
R = ρ × 1.2 × Loop length / Cable area + 0.002
Voltage drop (%) = Imp × R / String Vmp_STC × 100
Power loss (%) = Imp² × R / String power × 100
```

ค่าที่ใช้:

- Copper: `ρ = 0.0175 Ω·mm²/m`
- Aluminium: `ρ = 0.0282 Ω·mm²/m`
- `1.2` คือ temperature factor
- `0.002 Ω` คือ connector allowance

ในหน้า **สูตรคำนวณ** มีตารางตรวจสอบราย String แสดง One-way/Loop length,
ค่า ρ, temperature factor, ขนาดสาย, ความต้านทานตัวนำ, connector allowance
และความต้านทานรวม พร้อมตรวจ Voltage drop ทั้งหน่วย V และ %:

```text
Voltage drop (V) = Imp × Total R
Voltage drop (%) = Voltage drop (V) / String Vmp × 100
```

ตารางแสดงค่า Limit (%) และ `VD check = PASS/WARNING` ราย String

## 7. Output

| Output | รายละเอียด |
|---|---|
| Candidate strings | ผลแรงดัน/กระแสและสถานะราย String |
| Inverter summary | โหลดและ DC/AC ratio ราย `INVxx` |
| MPPT assignment | Inverter, MPPT และ input ของแต่ละ String |
| DC cable | ความต้านทาน, voltage drop และ power loss |
| QA/QC | Critical/Warning checks ก่อนใช้ผล |
| PVsyst preparation CSV | แยก sub-array ตาม Inverter, จำนวนแผง, orientation, tilt และ azimuth |
| Design Package JSON | Inputs, limits, inverter sets, strings และ assignments |

## 8. การรันและตรวจสอบ

```bash
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
python -m pytest -q
```

ก่อนนำผลไปใช้งานจริง ต้องตรวจอย่างน้อย:

1. รุ่น/รหัสต่อท้ายและ revision ของ datasheet
2. ค่า PAN/OND ที่ผ่านการยืนยัน
3. Tmin และ Tcell,max ของพื้นที่โครงการ
4. Ampacity, derating, installation method และ protection ของสาย
5. AC system, protection, grounding และข้อกำหนดการไฟฟ้า
6. String map และ cable route จากแบบ/หน้างานจริง
