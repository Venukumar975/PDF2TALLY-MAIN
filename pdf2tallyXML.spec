# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['믯憿獫慨慲畭桫㵡㈽㌮\u0a0d污慴物㴽⸶⸲റ愊瑬牧灡㵨〽ㄮ⸷വ愊祮潩㴽⸴㌱〮\u0a0d瑡牴㵳㈽⸶⸱ര戊楬歮牥㴽⸱⸹ര戊瑯汴㵥〽ㄮ⸳ഴ挊捡敨潴汯㵳㜽ㄮ㐮\u0a0d散瑲晩㵩㈽㈰⸶⸵〲\u0a0d晣楦㴽⸲⸰ര挊慨獲瑥渭牯慭楬敺㵲㌽㐮㜮\u0a0d汣捩㵫㠽㐮ㄮ\u0a0d汣彲潬摡牥㴽⸰⸳റ挊汯牯浡㵡〽㐮㘮\u0a0d牣灹潴牧灡票㴽㠴〮〮\u0a0d敄牰捥瑡摥㴽⸱⸳റ攊彴浸晬汩㵥㈽〮〮\u0a0d汆獡㵫㌽〮㈮\u0a0d汆獡\u2d6b潃獲㴽⸴⸰ര昊湯瑴潯獬㴽⸴㌶〮\u0a0d楧摴㵢㐽〮ㄮല䜊瑩祐桴湯㴽⸳⸱〵\u0a0dㅨ㴱〽ㄮ⸶ര栊瑴瑰潯獬㴽⸰⸸ര椊湤㵡㌽ㄮസ椊獴慤杮牥畯㵳㈽㈮〮\u0a0d慪潣癮㴽⸰⸵ര䨊湩慪㴲㌽ㄮ㘮\u0a0d獪湯捳敨慭㴽⸴㘲〮\u0a0d獪湯捳敨慭猭数楣楦慣楴湯㵳㈽㈰⸵⸹റ氊湡捧摯獥㴽⸳⸵റ氊湡畧条彥慤慴㴽⸱⸴ര氊浸㵬㘽ㄮㄮ\u0a0d慭楲慳琭楲㵥ㄽ㐮ㄮ\u0a0d慍歲灵慓敦㴽⸳⸰ള渊牡桷污㵳㈽㈮⸲റ渊浵祰㴽⸲⸴ശ漊数灮硹㵬㌽ㄮ㔮\u0a0d慰正条湩㵧㈽⸶ല瀊湡慤㵳㌽〮㌮\u0a0d摰浦湩牥献硩㴽〲㔲㈱〳\u0a0d摰灦畬扭牥㴽⸰ㄱ㤮\u0a0d数楦敬㴽〲㐲㠮㈮ശ瀊汩潬㵷ㄽ⸲⸲ര瀊潬汴㵹㘽㠮〮\u0a0d牰瑯扯晵㴽⸷㔳〮\u0a0d牰硯役潴汯㵳〽ㄮ〮\u0a0d祰牡潭㵲㤽㈮㔮\u0a0d祰牡潭\u2e72汣\u2e69潣敲㴽⸸⸱റ瀊慹牲睯㴽㐲〮〮\u0a0d祰灣牡敳㵲㌽〮\u0a0d祰敤正㴽⸰⸹ല瀊楹獮慴汬牥㴽⸶〲〮\u0a0d祰湩瑳污敬\u2d72潨歯\u2d73潣瑮楲㵢㈽㈰⸶ശ瀊歹歡獡㵩㈽㌮〮\u0a0d祰摰楦浵㴲㔽㤮〮\u0a0d祰桴湯搭瑡略楴㵬㈽㤮〮瀮獯ぴ\u0a0d祰桴湯洭汵楴慰瑲㴽⸰⸰㈳\u0a0d祰桴湯敮㵴㌽ㄮ〮\u0a0d祰敷癢敩㵷㘽㈮ㄮ\u0a0d祰楷㍮ⴲ瑣灹獥㴽⸰⸲ള倊她䵁㵌㘽〮㌮\u0a0d敲敦敲据湩㵧〽㌮⸷ര爊来硥㴽〲㘲㔮㤮\u0a0d敲畱獥獴㴽⸲㐳㈮\u0a0d灲獤瀭㵹㈽㈰⸶⸵റ猊瑥灵潴汯㵳㠽⸲⸰റ猊硩㴽⸱㜱〮\u0a0d浳慭㵰㔽〮㌮\u0a0d瑳牡敬瑴㵥ㄽ㈮ㄮ\u0a0d瑳敲浡楬㵴ㄽ㔮⸸ര琊湥捡瑩㵹㤽ㄮ㐮\u0a0d潴汭㴽⸰〱㈮\u0a0d祴楰杮敟瑸湥楳湯㵳㐽ㄮ⸵ര琊摺瑡㵡㈽㈰⸶ല甊楮潣敤慤慴㴲ㄽ⸷⸰റ甊汲楬㍢㴽⸲⸷ര甊楶潣湲㴽⸰㤴〮\u0a0d慷捴摨杯㴽⸶⸰ര眊扥潳正瑥㵳ㄽ⸶ര圊牥穫略㵧㌽ㄮ㠮\u0a0d牷灡㵴㈽㈮ㄮ\u0a0d', 'requests', 'click', 'flask', 'flask_cors', 'jinja2', 'werkzeug']
tmp_ret = collect_all('pdfplumber')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pypdfium2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('flask')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('aksharamukha')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['obf_dist\\desktop_run.py'],
    pathex=['obf_dist'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='pdf2tallyXML',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='pdf2tallyXML',
)
