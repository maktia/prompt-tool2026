"""提示詞填空小工具：把「文字內容.txt」做成 index.html。

用法（在 prompt-tool 資料夾裡）：
    python _build/build.py        依「文字內容.txt」產生 index.html 和 images-needed.md
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
TEXTS = os.path.join(TOOL, '文字內容.txt')

TAB_NAMES = {'scene': '場景分頁', 'both': '人物＋場景分頁'}          # 選項組只在某些分頁出現
OPT_TABS = {'單純人物': 'person', '場景': 'scene', '人物＋場景': 'both'}  # 單一選項只在某些分頁出現
NO_CUSTOM = {'ratio', 'avoid', 'place'}                               # 不加「自己寫」輸入框的組
TEXT_KEYS = {'subject': 'extra', 'scene': 'placeText', 'avoid': 'avoidText'}
DEFAULTS = {'avoid': ['v_text', 'v_wm']}
REMOVED_LABELS = {'場景分頁的游標提示', '分頁名稱（人物）', '感想區標題', '按鈕（清空）', '欄位名稱（參考資料，中文）', '欄位名稱（參考資料，英文）',
                  '參考資料句（中文，前半）', '參考資料句（中文，後半）', '參考資料句（英文，前半）', '參考資料句（英文，後半）'}

# (代號, 檔案裡顯示的名稱, 預設文字)；名稱裡不要有全形冒號
UI_SPEC = [
    ('pageTitle', '瀏覽器分頁標題', '提示詞填空小工具'),
    ('h1', '大標題', '提示詞填空小工具'),
    ('intro', '大標題下的說明', '一格一格點選，就能組出可以貼給 Gemini 或 ChatGPT 生圖的提示詞。腦袋空空時，按「隨機幫我填」。'),
    ('tabPerson', '分頁名稱（單純人物）', '單純人物'),
    ('tabScene', '分頁名稱（場景）', '場景'),
    ('tabBoth', '分頁名稱（人物加場景）', '人物＋場景'),
    ('outTitle', '右側區塊標題', '你的提示詞'),
    ('langZh', '語言按鈕（中文）', '中文'),
    ('langEn', '語言按鈕（英文）', 'English'),
    ('prefixLabel', '開頭句勾選框說明', '開頭加上「請幫我生成一張圖片」（建議開著，AI 才會直接生圖，而不是只回答文字）'),
    ('outPlaceholder', '提示詞框空白時的提示', '在左邊點選卡片，提示詞就會出現在這裡。'),
    ('btnCopy', '按鈕（複製）', '複製提示詞'),
    ('btnGemini', '按鈕（開啟 Gemini）', '複製並開啟 Gemini'),
    ('btnGpt', '按鈕（開啟 ChatGPT）', '複製並開啟 ChatGPT'),
    ('btnRandom', '按鈕（隨機）', '隨機幫我填'),
    ('tip', '小技巧說明', '小技巧：生完圖後，一次只改一格再重新生，才看得出是哪個選項讓畫面變了。風格請用「畫法」描述，不要填畫家的名字。'),
    ('missPrefix', '缺項提示（前半）', '還沒選：'),
    ('missSuffix', '缺項提示（後半）', '（沒選也可以，AI 會自己決定）'),
    ('missNames', '缺項名稱（依序是人物類型、場景、鏡頭距離、鏡頭角度、光影、風格）', ['人物類型', '場景', '鏡頭距離', '鏡頭角度', '光影', '風格']),
    ('copyOk', '複製成功訊息', '已複製！到 AI 的對話框貼上就可以了。'),
    ('copyEmpty', '沒有內容可複製的訊息', '還沒有內容可以複製，先在左邊點選幾個選項吧。'),
    ('copyFail', '複製失敗訊息', '複製失敗，請手動選取上面的文字複製。'),
    ('headZh', '提示詞開頭句（中文）', '請幫我生成一張圖片。'),
    ('headEn', '提示詞開頭句（英文）', 'Please generate an image.'),
    ('labZh', '欄位名稱（中文，依序是主體、場景、鏡頭、光影、風格、畫面比例、不要出現）', ['主體', '場景', '鏡頭', '光影', '風格', '畫面比例', '不要出現']),
    ('labEn', '欄位名稱（英文，順序同上）', ['Subject', 'Setting', 'Camera', 'Lighting', 'Style', 'Aspect ratio', 'Avoid']),
    ('hairWord', '只選髮色時加在後面的字（組成提示詞用）', '頭髮'),
    ('customPh', '自己寫的輸入框提示字', '選項沒有的，自己寫在這裡（選填）'),
    ('transNote', '英文版沒有翻譯時的提醒', '英文版裡你自己寫的字會維持中文（Gemini、ChatGPT 看得懂）。用電腦版 Chrome 可以自動翻成英文。'),
    ('modalTitle', '複製後跳出視窗的標題', '提示詞複製好了！等 AI 生圖的時候，來回答幾個小問題吧'),
    ('modalIntro', '複製後跳出視窗的說明', '先到 Gemini 或 ChatGPT 貼上提示詞、按下生圖。等圖片出來的空檔，可以先回答下面第一部分。'),
    ('fbPart1', '問卷第一部分標題', '現在就可以回答'),
    ('fbPart2', '問卷第二部分標題', '圖片出來後再回答（可以先關掉，之後按右下角的按鈕回來）'),
    ('qWait', '等圖時的思考題', '想一想：看到圖之後，你最想改哪一格？'),
    ('qWaitOpts', '思考題選項', ['風格', '人物', '場景', '鏡頭', '光影', '不要什麼', '都滿意']),
    ('btnLater', '按鈕（先收起來）', '先收起來，等圖出來再回來'),
    ('btnReopen', '右下角按鈕（回來答問卷）', '回答小問卷'),
    ('fbNote', '感想區說明', '不用寫名字，大約 1 分鐘。你按「送出」才會傳送，不想填也沒關係。'),
    ('q1', '感想第 1 題', '① 這個提示詞工具對你有幫助嗎？'),
    ('q1Opts', '第 1 題的五個等級說明', ['完全沒有', '不太有', '普通', '有幫助', '非常有']),
    ('q2', '感想第 2 題', '② 生出來的圖，有達到你想要的效果嗎？'),
    ('q2Opts', '第 2 題選項（送出的資料一律用中文）', ['完全達到', '大致達到', '有一點落差', '沒有達到', '還沒去生圖']),
    ('q3', '感想第 3 題', '③ 你用哪個 AI 生圖？'),
    ('q3Opts', '第 3 題選項（送出的資料一律用中文）', ['Gemini', 'ChatGPT', '其他']),
    ('q4', '感想第 4 題', '④ 哪裡好用？哪裡需要改進？（選填）'),
    ('q4Ph', '第 4 題輸入框的提示字', '例如：鏡頭選項很清楚，但我想要更多服裝選擇'),
    ('consent', '同意附上提示詞的勾選說明', '我同意把剛剛組出的提示詞一起送給老師（選填，方便老師看哪裡可以改進）'),
    ('submit', '按鈕（送出感想）', '送出感想'),
    ('fbNeedQ1', '沒答第 1 題的提醒', '請先回答第 ① 題（有沒有幫助）。'),
    ('fbNoForm', '老師還沒設定表單時的訊息', '老師還沒有設定回收表單，這次感想沒有送出。（設定方法請看 README.md）'),
    ('fbOk', '送出成功訊息', '已送出，謝謝你的感想！'),
    ('fbErr', '送出失敗訊息', '送出失敗，請檢查網路後再試一次。'),
    ('footer', '頁面最下方的說明', '這個工具不會蒐集你的姓名或帳號。你選的內容只存在你自己的瀏覽器裡；只有你按「送出感想」才會把感想送出。'),
]


def split_bi(s):
    """「中文 / English」拆成兩段；沒有英文就回傳 (中文, '')。"""
    parts = re.split(r'\s+/\s+', s.strip(), maxsplit=1)
    return (parts[0].strip(), parts[1].strip() if len(parts) > 1 else '')


def as_list(s):
    return [x.strip() for x in s.split('|')]


# ---------------------------------------------------------------- 讀文字檔
def parse_texts():
    by_label = {label: (key, default) for key, label, default in UI_SPEC}
    zh = {key: default for key, label, default in UI_SPEC}
    en = {}
    cards, cur, grp, section = [], None, None, None
    with open(TEXTS, encoding='utf-8-sig') as f:
        lines = f.read().splitlines()
    for ln, raw in enumerate(lines, 1):
        s = raw.strip()
        if not s or s.startswith('#'):
            continue
        if s.startswith('■ 網頁文字'):
            section, cur, grp = 'ui', None, None
            continue
        m = re.match(r'■\s*卡片\s*\d+\s*〔(\w+)〕', s)
        if m:
            section, grp = 'card', None
            cur = {'key': m.group(1), 'title': '', 'titleEn': '', 'hint': '', 'hintEn': '', 'text': None, 'groups': []}
            cards.append(cur)
            continue
        m = re.match(r'▸\s*(.*?)\s*〔(\w+)｜(單選|多選\d*)｜(圖塊|文字鈕)(?:｜([^〕]+))?〕', s)
        if m and cur is not None:
            mt = m.group(3)
            mx = int(mt[2:]) if mt.startswith('多選') and mt[2:] else (99 if mt.startswith('多選') else 1)
            label, label_en = split_bi(m.group(1))
            grp = {'key': m.group(2), 'label': label, 'labelEn': label_en, 'mode': 'single' if mt == '單選' else 'multi', 'max': mx,
                   'view': 'tile' if m.group(4) == '圖塊' else 'chip', 'opts': []}
            if m.group(5):
                names = [x.strip() for x in m.group(5).split('、')]
                grp['tabs'] = [k for k, v in TAB_NAMES.items() if v in names]
            grp['custom'] = grp['key'] not in NO_CUSTOM
            cur['groups'].append(grp)
            continue
        if section == 'ui':
            if '：' not in s:
                raise SystemExit('第 %d 行看不懂（少了「：」）：%s' % (ln, s))
            label, val = s.split('：', 1)
            label = label.strip()
            if label in REMOVED_LABELS:
                continue
            if label not in by_label:
                raise SystemExit('第 %d 行的名稱不認得：「%s」（名稱請不要改）' % (ln, label))
            key, default = by_label[label]
            zh_part, en_part = split_bi(val)
            if isinstance(default, list):
                zh[key] = as_list(zh_part)
                if en_part:
                    en[key] = as_list(en_part)
            else:
                zh[key] = zh_part
                if en_part:
                    en[key] = en_part
        elif section == 'card' and cur is not None:
            if grp is not None and '|' in s and '：' not in s.split('|')[0]:
                parts = [x.strip() for x in s.split('|')]
                if len(parts) < 3 or not parts[0] or not parts[1]:
                    raise SystemExit('第 %d 行的選項格式不對（要「代號 | 中文 | English | 圖示」）：%s' % (ln, s))
                op = {'id': parts[0], 'zh': parts[1], 'en': parts[2], 'icon': parts[3] if len(parts) > 3 else ''}
                for tok in parts[4:]:
                    if not tok:
                        continue
                    if tok.startswith('英='):
                        op['labelEn'] = tok[2:].strip()
                    elif tok.startswith('色='):
                        op['color'] = tok[2:].strip()
                    else:
                        op['tabs'] = [OPT_TABS[n.strip()] for n in tok.split('、') if n.strip() in OPT_TABS]
                grp['opts'].append(op)
            elif s.startswith('標題：'):
                cur['title'], cur['titleEn'] = split_bi(s[3:])
            elif s.startswith('說明：'):
                cur['hint'], cur['hintEn'] = split_bi(s[3:])
            elif s.startswith('補充欄標題：'):
                cur['text'] = cur['text'] or {'key': TEXT_KEYS.get(cur['key'], cur['key'] + 'Text'), 'label': '', 'labelEn': '', 'placeholder': '', 'placeholderEn': ''}
                cur['text']['label'], cur['text']['labelEn'] = split_bi(s[6:])
            elif s.startswith('補充欄提示：'):
                cur['text'] = cur['text'] or {'key': TEXT_KEYS.get(cur['key'], cur['key'] + 'Text'), 'label': '', 'labelEn': '', 'placeholder': '', 'placeholderEn': ''}
                cur['text']['placeholder'], cur['text']['placeholderEn'] = split_bi(s[6:])
            else:
                raise SystemExit('第 %d 行看不懂：%s' % (ln, s))
    ids = set()
    for n, c in enumerate(cards, 1):
        c['num'] = n
        for g in c['groups']:
            if not g['opts']:
                raise SystemExit('「%s」沒有任何選項' % g['label'])
            for op in g['opts']:
                if op['id'] in ids:
                    raise SystemExit('選項代號重複：%s' % op['id'])
                ids.add(op['id'])
    # 英文介面：沒寫英文的文字就沿用中文
    en_full = {k: en.get(k, v) for k, v in zh.items()}
    return cards, {'zh': zh, 'en': en_full}


# ---------------------------------------------------------------- 產生網頁
FIXED_ICONS = ['palette', 'content_copy', 'open_in_new', 'casino', 'chat', 'send', 'close']


def build():
    cards, ui = parse_texts()
    icons = set(FIXED_ICONS)
    for c in cards:
        for g in c['groups']:
            for op in g['opts']:
                if op['icon']:
                    icons.add(op['icon'])
    data = {'cards': cards, 'defaults': DEFAULTS, 'ui': ui}
    with open(os.path.join(HERE, 'template.html'), encoding='utf-8-sig') as f:
        html = f.read()
    with open(os.path.join(HERE, 'style.css'), encoding='utf-8') as f:
        css = f.read()
    html = html.replace('/*__STYLE__*/', css).replace('__ICON_NAMES__', ','.join(sorted(icons))).replace('__DATA__', json.dumps(data, ensure_ascii=False))
    with open(os.path.join(TOOL, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    write_images_md(cards)
    print('已產生 index.html（%d 張卡片）' % len(cards))


def write_images_md(cards):
    by = {g['key']: g for c in cards for g in c['groups']}
    base = '穿黃色雨衣、黑色短髮的少女站在雨天的小書店裡'

    def prompt(shot='半身', angle='平視', light='柔光', style='扁平插畫'):
        return '請幫我生成一張 4:3 的圖片：%s，%s、%s，%s，%s風格。不要出現任何文字、浮水印。' % (base, shot, angle, light, style)
    scene_base = '請幫我生成一張 4:3 的圖片：雨天的小書店，%s，柔和自然光，扁平插畫風格。不要出現任何文字、浮水印。'
    rows = []
    for key, where, fn in [('distance', '鏡頭｜距離（人物）', lambda x: prompt(shot=x)), ('sceneDistance', '鏡頭｜距離（場景）', lambda x: scene_base % x),
                           ('angle', '鏡頭｜角度', lambda x: prompt(angle=x)),
                           ('light', '光影', lambda x: prompt(light=x)), ('style', '風格', lambda x: prompt(style=x))]:
        if key in by:
            for op in by[key]['opts']:
                rows.append((op['id'] + '.jpg', where, op['zh'], fn(op['zh'])))
    md = ['# 選項縮圖清單（用 Gemini 生圖）', '',
          '工具裡「鏡頭、光影、風格」三張卡片的選項可以放縮圖。沒有圖時會自動改顯示圖示（或什麼都不顯示），所以**可以先不放圖**，生好再補。', '',
          '## 做法', '',
          '1. 到 Gemini，依下表每一列的「提示詞」生一張圖（同一位角色、同一個場景，只換一個條件，學生才看得出差別）。',
          '2. 圖片存成 JPG，**檔名照表格的「檔名」欄**（例如 `d_long.jpg`），建議寬 600 到 800 像素、單張 150 KB 以下。',
          '3. 全部放進 `prompt-tool/img/` 資料夾，重新整理網頁就會出現。', '',
          '提醒：生出來的角色每張可能長得不太一樣，可以在提示詞前面加「角色維持與上一張相同」，或用同一個對話連續生成。', '',
          '| 檔名 | 用在哪 | 選項 | 給 Gemini 的提示詞 |', '|---|---|---|---|']
    for fn, where, name, p in rows:
        md.append('| `%s` | %s | %s | %s |' % (fn, where, name, p))
    md += ['', '共 %d 張。' % len(rows)]
    with open(os.path.join(TOOL, 'images-needed.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))


if __name__ == '__main__':
    build()
