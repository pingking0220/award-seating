"""截圖 + 自動標號：用範例資料（離線、不連 Firebase）拍操作說明用的畫面。"""
import io, os, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont

REPO = Path(r"C:\Users\User\award-seating")
OUT = REPO / "guide"
OUT.mkdir(exist_ok=True)
URL = (REPO / "index.html").as_uri()
FONT = ImageFont.truetype(r"C:\Windows\Fonts\msjhbd.ttc", 22)
RED = (220, 38, 38)

SAMPLE = """
(() => {
  const D = currentDate, S = {};
  const put = (k, dept, classNo, award, name) => S[k] = {dept, classNo, award, name};
  put('1-1-2','edu','101','閱讀楷模','王小明'); put('1-1-3','edu','102','閱讀楷模','林小華');
  put('1-1-4','edu','103','閱讀楷模','陳小安'); put('2-1-2','edu','201','語文競賽','張小美');
  put('2-1-3','edu','202','語文競賽','李小傑');
  put('3-0-1','stu','301','模範生','黃大文'); put('3-0-2','stu','302','模範生','吳佳佳');
  put('3-0-3','stu','303','模範生','周子涵'); put('4-0-1','stu','401','體育績優','劉宇軒');
  put('3-2-0','cou','501','孝親楷模','蔡依林'); put('3-2-1','cou','502','孝親楷模','鄭凱文');
  put('4-2-0','cou','503','','');
  put('5-2-2','kin','大班','全勤獎','小芸'); put('5-2-3','kin','大班','全勤獎','小宇');
  allData = {}; allData[D] = S; seats = S; renderAll();
})();
"""

def as_role(page, role):
    page.evaluate("""role => {
      hideLoginGate(); myRole = role; myEmail = role === 'admin' ? 'it@lsps.tp.edu.tw' : 'teacher@lsps.tp.edu.tw';
      myEmailKey = emailToKey(myEmail); updateUserPill({}); applyRole(); setSync(true);
    }""", role)

def box(page, sels):
    """一個或多個 selector 的聯集外框（viewport 座標）"""
    if isinstance(sels, str): sels = [sels]
    bs = []
    for s in sels:
        loc = page.locator(s)
        for i in range(loc.count()):
            b = loc.nth(i).bounding_box()
            if b and b["width"] > 0: bs.append(b)
    if not bs: raise RuntimeError("找不到元素：%s" % sels)
    x1 = min(b["x"] for b in bs); y1 = min(b["y"] for b in bs)
    x2 = max(b["x"] + b["width"] for b in bs); y2 = max(b["y"] + b["height"] for b in bs)
    return [x1, y1, x2, y2]

def shot(page, name, marks, clip=None, pad=24):
    """marks: [(selector(s), 標號, 標號位置 'tl'/'tr'/'l'/'r')]；clip: 裁切範圍的 selector"""
    rects = [(box(page, s), n, pos) for s, n, pos in marks]
    img = Image.open(io.BytesIO(page.screenshot(full_page=True))).convert("RGB")
    ox = oy = 0
    if clip:
        c = box(page, clip)
        ox, oy = max(0, c[0] - pad), max(0, c[1] - pad)
        img = img.crop((ox, oy, min(img.width, c[2] + pad), min(img.height, c[3] + pad)))
    d = ImageDraw.Draw(img)
    for (x1, y1, x2, y2), n, pos in rects:
        x1, y1, x2, y2 = x1 - ox - 4, y1 - oy - 4, x2 - ox + 4, y2 - oy + 4
        d.rounded_rectangle([x1, y1, x2, y2], radius=8, outline=RED, width=3)
        r = 16
        cx, cy = {"tl": (x1, y1), "tr": (x2, y1), "l": (x1 - r - 4, (y1 + y2) / 2),
                  "r": (x2 + r + 4, (y1 + y2) / 2), "bl": (x1, y2)}[pos]
        cx = min(max(cx, r + 2), img.width - r - 2); cy = min(max(cy, r + 2), img.height - r - 2)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=RED, outline="white", width=2)
        d.text((cx, cy), str(n), font=FONT, fill="white", anchor="mm")
    img.save(OUT / (name + ".png"), optimize=True)
    print("saved", name)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 2000, "height": 1400}, device_scale_factor=1)
    ctx.add_init_script("window.print = () => {};")
    ctx.route("**/*gstatic.com/**", lambda r: r.abort())   # 不載入 Firebase → 絕不會寫到正式資料庫
    page = ctx.new_page()
    page.goto(URL); page.wait_for_timeout(800)
    page.evaluate("document.getElementById('login-msg').textContent=''")

    # 1 登入
    shot(page, "01-login", [("#btn-login", 1, "r")], clip=".login-card", pad=60)
    # 14 LINE/FB 內建瀏覽器提示
    page.evaluate("""Object.defineProperty(navigator,'userAgent',{value:'Mozilla/5.0 [FBAN/FB4A;FBAV/450.0]',configurable:true}); checkInAppBrowser();""")
    shot(page, "14-inapp", [("#login-msg", 1, "l")], clip=".login-card", pad=60)
    page.evaluate("Object.defineProperty(navigator,'userAgent',{value:'Mozilla/5.0 Chrome/130',configurable:true}); document.getElementById('login-msg').textContent=''")

    # 2 首次選處室
    page.evaluate("hideLoginGate(); myRole=null; applyRole(); document.getElementById('deptpick-overlay').classList.add('show')")
    shot(page, "02-deptpick", [("#deptpick-overlay .dept-pick-btn", 1, "l"),
                              ("#deptpick-overlay .modal-btns button", 2, "l")], clip="#deptpick-overlay .modal")
    page.evaluate("closeDeptPick()")

    # 3 主畫面（教務處身分）
    page.evaluate(SAMPLE); as_role(page, "edu")
    shot(page, "03-main", [
        ("#user-pill", 1, "tl"), ("#dept-edu", 2, "tl"),
        (["#btn-movemode", "button[onclick='showHistory()']"], 3, "tl"),
        (["button[onclick='exportCSV()']", "#btn-guide"], 4, "tl"),
        ("#role-banner", 5, "l"), ("#fields .field:first-child", 6, "tl"),
        (["#f-class", "#f-name"], 7, "tl"), ("#seating-outer", 8, "tl"), ("#status-bar", 9, "l")])

    # 4 填資料 + 拖曳框選
    page.fill("#f-class", "601"); page.fill("#f-award", "服務熱心"); page.fill("#f-name", "許小晴")
    a = page.locator("#seat-6-1-1").bounding_box(); z = page.locator("#seat-7-1-3").bounding_box()
    page.mouse.move(a["x"] + 20, a["y"] + 20); page.mouse.down()
    page.mouse.move(z["x"] + 40, z["y"] + 40, steps=8)
    shot(page, "04-drag", [(["#f-class", "#f-name"], 1, "tl"), ("#drag-rect", 2, "l")],
         clip=["#fields", "#seat-8-2-3"])
    page.mouse.up(); page.wait_for_timeout(200)
    # 5 確認預約視窗
    shot(page, "05-confirm", [("#preview-grid", 1, "l"), ("#summary", 2, "l"), ("#btn-confirm", 3, "tr")],
         clip="#overlay .modal")
    page.click("#btn-confirm"); page.wait_for_timeout(300)

    # 6 點已預約座位 → 編輯／解除
    page.click("#seat-1-1-2"); page.wait_for_timeout(200)
    shot(page, "06-edit", [("#release-edit", 1, "l"), ("#btn-release-save", 2, "bl"), ("#btn-release-del", 3, "bl")],
         clip="#release-overlay .modal")
    page.evaluate("closeRelease()")

    # 15 單一座位拖曳（拍完移回原位放開＝取消）
    x1, y1 = page.locator("#seat-1-1-3").bounding_box()["x"] + 40, page.locator("#seat-1-1-3").bounding_box()["y"] + 36
    t = page.locator("#seat-5-1-5").bounding_box()
    page.mouse.move(x1, y1); page.mouse.down(); page.mouse.move(t["x"] + 40, t["y"] + 36, steps=10)
    shot(page, "15-move-single", [("#seat-1-1-3", 1, "l"), ("#seat-5-1-5", 2, "r")], clip=["#stage", "#seat-6-2-3"], pad=10)
    page.mouse.move(x1, y1, steps=5); page.mouse.up(); page.wait_for_timeout(100)

    # 16 移動模式：框選兩席 → 整批拖曳（拍完移回原位放開＝取消）
    page.click("#btn-movemode"); page.wait_for_timeout(2600)
    a = page.locator("#seat-2-1-1").bounding_box(); z = page.locator("#seat-2-1-3").bounding_box()
    page.mouse.move(a["x"] - 20, a["y"] + 10); page.mouse.down(); page.mouse.move(z["x"] + 60, z["y"] + 60, steps=8); page.mouse.up()
    page.wait_for_timeout(2600)
    s0 = page.locator("#seat-2-1-2").bounding_box(); t = page.locator("#seat-8-1-4").bounding_box()
    page.mouse.move(s0["x"] + 40, s0["y"] + 36); page.mouse.down(); page.mouse.move(t["x"] + 40, t["y"] + 36, steps=10)
    shot(page, "16-move-group", [("#btn-movemode", 1, "tl"), (["#seat-2-1-2", "#seat-2-1-3"], 2, "l"),
                                 (["#seat-8-1-4", "#seat-8-1-5"], 3, "l")], clip=["header", "#seat-9-2-3"], pad=0)
    page.mouse.move(s0["x"] + 40, s0["y"] + 36, steps=5); page.mouse.up(); page.wait_for_timeout(100)
    page.evaluate("toggleMoveMode()"); page.wait_for_timeout(2600)

    # 7 框選刪除
    page.click("#btn-delmode"); page.wait_for_timeout(2600)
    a = page.locator("#seat-2-1-2").bounding_box(); z = page.locator("#seat-2-1-3").bounding_box()
    page.mouse.move(a["x"] + 10, a["y"] + 10); page.mouse.down()
    page.mouse.move(z["x"] + 60, z["y"] + 60, steps=8)
    shot(page, "07-delmode", [("#btn-delmode", 1, "tl"), ("#drag-rect", 2, "l")], clip=["header", "#seat-5-2-3"], pad=0)
    page.mouse.up(); page.wait_for_timeout(200)
    page.evaluate("closeModal(); toggleDelMode()"); page.wait_for_timeout(2600)

    # 8 全部刪除
    page.evaluate("showClearAll()")
    shot(page, "08-clearall", [("#clear-overlay .modal-btns button:first-child", 1, "l")], clip="#clear-overlay .modal")
    page.evaluate("closeClearAll()")

    # 9 匯入名單
    page.evaluate("""() => { showImport(); parseImportRows([
      {日期: currentDate, 排:'8', 區:'中', 座號:'1', 處室:'教務處', 班級:'602', 獎項:'科展佳作', 姓名:'蘇小雨'},
      {日期: currentDate, 排:'8', 區:'中', 座號:'2', 處室:'教務處', 班級:'603', 獎項:'科展佳作', 姓名:'方小宇'},
      {日期: currentDate, 排:'2', 區:'中', 座號:'3', 處室:'教務處', 班級:'101', 獎項:'閱讀楷模(特優)', 姓名:'王小明'},
      {日期: currentDate, 排:'4', 區:'左', 座號:'2', 處室:'教務處', 班級:'', 獎項:'', 姓名:''},
      {日期: currentDate, 排:'4', 區:'左', 座號:'2', 處室:'學務處', 班級:'', 獎項:'', 姓名:''}]); }""")
    shot(page, "09-import", [("button[onclick='downloadTemplate()']", 1, "tl"), ("label:has(#import-file)", 2, "tr"),
                             ("#import-result", 3, "l"), ("#btn-import-confirm", 4, "l")], clip="#import-overlay .modal")
    page.evaluate("closeImport()")

    # 10 復原：先做兩次刪除產生紀錄
    page.evaluate("""() => { persist(currentDate, {'2-1-2': null}, '', '解除預約');
                             persist(currentDate, {'2-1-3': null}, '', '框選刪除'); showHistory(); }""")
    page.wait_for_timeout(200)
    shot(page, "10-history", [("#history-scope", 1, "l"), ("#history-list .hist-row:first-child button", 2, "l")],
         clip="#history-overlay .modal")
    page.evaluate("closeHistory()")

    # 11 列印通知單（彈出視窗）
    with page.expect_popup() as pop:
        page.evaluate("printSlips()")
    pp = pop.value; pp.set_viewport_size({"width": 900, "height": 700}); pp.wait_for_timeout(500)
    img = Image.open(io.BytesIO(pp.screenshot())).convert("RGB"); img.save(OUT / "11-slips.png", optimize=True)
    print("saved 11-slips"); pp.close()

    # 12 總覽模式
    page.mouse.move(5, 900); page.evaluate("toggleOverview()"); page.wait_for_timeout(300)
    shot(page, "12-overview", [("#overview-exit", 1, "l"), ("#overview-info", 2, "l")])
    page.evaluate("toggleOverview()")

    # 13 成員管理（管理者）
    as_role(page, "admin")
    page.evaluate("""() => { renderMembers({'it@lsps,tp,edu,tw':'admin','teacher-a@lsps,tp,edu,tw':'edu',
        'teacher-b@lsps,tp,edu,tw':'stu','teacher-c@lsps,tp,edu,tw':'cou','teacher-d@lsps,tp,edu,tw':'kin'});
        document.getElementById('members-overlay').classList.add('show'); }""")
    shot(page, "13-members", [("#members-list .mem-row:nth-child(2) button", 1, "tr"),
                              (["#mem-email", "#members-overlay .tool-btn"], 2, "tl")], clip="#members-overlay .modal")
    b.close()
