"""
English for the Chinese words and phrases that occur in the bulk-import sources.

apps.products.import_text.clean_text uses them in two ways. SUBSTRINGS are replaced
wherever they occur, longest first together with its own GLOSSARY, so a phrase wins over
the single characters inside it ('独立显卡' is 'discrete graphics', not '独' + '立' =
vertical). RUNS translate a run of Chinese text only when the whole run is the phrase -
the way the notes in firmware file names occur ('25Q64CV 不显BF 刷了VLAB故障一样') - so a
word is never translated out of a sentence that is otherwise dropped (a datasheet's
'具有' is not turned into 'has'). They were translated by hand from each phrase's
context in the sources:

- firmware dump file names written by repair technicians (亮机 = the machine boots with a
  picture, 不显 = no display, 掉电 = power cuts out, 刷 = flash, 合成 = merged image,
  BF = backup, kept as written);
- factory BOM lines (colours, clips, labels, and approved-vendor names);
- schematic and service-manual file names.

Vendor names are the company's own English name where it is known; where it isn't, the
name is romanized (marked "romanized").
"""

SUBSTRINGS = {
    # phrases that single-character entries in GLOSSARY would otherwise break
    '独立显卡': ' discrete graphics ', '独立': ' discrete ', '立昌先進': 'Ceratech', '立昌': 'Ceratech',
    '烧穿': ' burnt through ', '燒穿': ' burnt through ', '燒錄': ' programmed ', '烧录': ' programmed ',
    '开机无显示': ' no display at power-on ', '无显示': ' no display ', '无报错': ' no errors ',
    '无需滤波': ' filterless ',
    # brand names
    '联想': 'Lenovo ', '惠普': 'HP ', '戴尔': 'Dell ', '东芝': 'Toshiba ', '宏基': 'Acer ', '技嘉': 'Gigabyte ',
    '华擎': 'ASRock ', '微星': 'MSI ', '索尼': 'Sony ', '华为': 'Huawei ', '神舟': 'Hasee ', '机械革命': 'Mechrevo ',
    '黑马维修网': '',
}

RUNS = {
    '？': '?',
    # --- brands and product lines ---
    '联想一体机': 'Lenovo all-in-one ', '联想一体': 'Lenovo all-in-one ',
    '联想杨天': 'Lenovo Yangtian ', '联想扬天': 'Lenovo Yangtian ', '联想昭阳': 'Lenovo Zhaoyang ',
    '昭阳': 'Zhaoyang ', '联想小新': 'Lenovo Xiaoxin ',
    '三星': 'Samsung ', '三量': 'Samsung ', '小米': 'Xiaomi ', '小米笔记本': 'Xiaomi notebook ',
    '神州': 'Hasee ', '神舟战神': 'Hasee Ares ', '战神': 'Ares ', '战神备份': 'Ares backup ',
    '械革命': 'Mechrevo ', '深海泰坦': 'Deep Sea Titan ', '炫龙': 'Shinelon ',
    '橘子': 'Juzi ', '天运': 'Tianyun ', '火神': 'Vulcan ', '乐趣': 'Lequ ', '淘宝': 'Taobao ', '淘': 'Taobao ',
    '英业达集成': 'Inventec integrated ', '华邦刷确定': 'Winbond, flashed, confirmed ',
    '鹅城巴图鲁制作': ' (made by Echeng Baturu)', '杨天': 'Yangtian ', '扬天': 'Yangtian ', '小新': 'Xiaoxin ',
    '一体': ' all-in-one ', '原厂机器': ' factory machine ', '原厂机': ' factory machine ', '拆好机上的': 'from a working ',

    # --- firmware dump notes: what the dump is ---
    '官网合成': ' official, merged ', '官网分离': ' official, split ', '官方合成': ' official merged ',
    '官方提取': ' extracted from official ', '官方': ' official ', '官网': ' official ', '代官网': '-gen official ',
    '合成已配置': ' merged, configured ', '合成屏蔽内存': ' merged, onboard RAM disabled ', '通用合成': ' generic merged ',
    '自己合成': ' self-merged ', '分离合成': ' split and merged ', '仅合成': ' merged only ', '合成': ' merged ',
    '合': ' merged ', '分离': ' split ', '提取': ' extracted ', '读取': ' read ', '读': ' read ',
    '原厂': ' factory original ', '三星原厂': 'Samsung factory original ', '东芝原厂机器': 'Toshiba factory machine ',
    '东芝原厂机': 'Toshiba factory machine ', '原机': ' original machine ', '原机亮': ' original machine, displays ',
    '原机备份': ' original machine backup ', '原机备份好': ' original machine backup, good ',
    '原机备份桥': ' original machine backup, bridge ', '原机备份版号': ' original machine backup, board no. ',
    '原机版号': ' original board no. ', '三星原机修改版号': 'Samsung original machine, board no. modified ',
    '原': ' original ', '原本': ' originally ', '工厂': ' factory ', '工厂原始测试版': ' factory original test version ',
    '工厂干密码': ' factory, password removed ', '公版': ' reference version ', '纯净': ' clean ',
    '绝对正版': ' genuine ', '副本': ' copy ', '缩小版': ' reduced version ', '缩小': ' reduced ', '终极': ' ultimate ',
    '备份': ' backup ', '备份出来': ' backed up ', '编程器备份': ' programmer backup ', '机器备份': ' machine backup ',
    '好机备份': ' backup from a working machine ', '好机器': ' working machine ', '好的': ' good ', '好': ' good ',
    '好一个': ' a good one ', '亮机备份': ' display-OK backup ', '板载集成亮机备份': ' onboard integrated, display-OK backup ',
    '桥亮机备份': ' bridge, display-OK backup ', '不显备份': ' no-display backup ', '短路备份': ' short-circuit backup ',
    '短路暂时备份起来': ' short circuit, backed up for now ', '报错机器备份': ' backup from a machine reporting errors ',
    '关机重启备份': ' restarts on shutdown, backup ', '屏蔽工程模式报错后备份': ' backup after suppressing the engineering-mode error ',
    '有密码的机器备份出来': ' backed up from a password-locked machine ', '有密码备份清除': ' password backup cleared ',
    '上换键盘机器备份出来的': ' backed up from a machine with a replaced keyboard ', '网上别人备份出来的单': ' single backup from the web ',
    '未知自己备份': ' unknown, own backup ', '内部程序备份好': ' internal firmware backup, good ', '进液备份': ' liquid damaged, backup ',
    '同学的料板读取': " read from a classmate's spare board ", '拆好机上的联想': 'from a working Lenovo ',
    '网上下载的': ' downloaded from the web ', '网上下未测试': ' downloaded from the web, untested ', '网上下': ' downloaded from the web ',
    '网上买刷好': ' bought pre-flashed online ', '买的': ' bought ', '买': ' bought ', '随机': ' shipped with ',
    '资料': ' data ', '码片': ' BIOS chip ', '程序': ' firmware ', '内部程序': ' internal firmware ', '独显程序': ' discrete graphics firmware ',
    '中文': ' Chinese ', '加拿大版': ' Canadian version ', '白名单': ' whitelist ', '包好': ' guaranteed good ', '包': ' guaranteed ',
    '捕获': ' capture ', '写着': ' labelled ', '已清除': ' cleared ', '已配置': ' configured ', '已改': ' modified ',
    '修改': ' modified ', '改过': ' modified ', '改好': ' modified ', '改': ' modified ', '未改': ' unmodified ',
    '改集显': ' modified for integrated graphics ', '改集显也刷这个': ' for the integrated-graphics mod, flash this too ',
    '改通用': ' modified to generic ', '改工程模式': ' engineering mode modified ', '可改普通模式': ' can be set to normal mode ',
    '普通模式': ' normal mode ', '解密': ' unlocked ', '解密要刷': ' to unlock, flash ',

    # --- firmware dump notes: board and machine ---
    '板号': ' board no. ', '版号': ' board no. ', '版号是': ' board no. is ', '代版号': '-gen board no. ',
    '独显版号': ' discrete graphics board no. ', '机器型号': ' machine model ', '型号': ' model ', '号': ' no. ',
    '一体机': ' all-in-one ', '超极本': ' ultrabook ', '三星上网本': 'Samsung netbook ', '一体板带': ' all-in-one board with ',
    '一体板': ' all-in-one board ', '大显卡板': ' large graphics board ', '小板': ' small board ', '蓝板': ' blue board ',
    '主板': ' mainboard ', '主板上': ' on the mainboard ', '代主板上测亮机': '-gen mainboard, tested, displays ', '板': ' board ',
    '屏': ' screen ', '的屏': ' screen ', '机器': ' machine ', '主': ' main ', '右': ' right ', '单': ' single ',
    '单利': ' single ', '双': ' dual ', '两': ' two ', '大': ' large ', '脚': '-pin', '芯片': ' chip ', '芯片组': ' chipset ',
    '架构': ' architecture ', '北桥': ' northbridge ', '南桥': ' southbridge ', '南桥旁': ' next to the southbridge ',
    '集显南桥': ' integrated graphics southbridge ', '独显楠桥': ' discrete graphics southbridge ', '桥': ' bridge ',
    '边的': ' next to the ', '桥边的': ' next to the bridge ', '在桥旁边': ' next to the bridge ', '单桥': ' single bridge ',
    '单桥独显': ' single bridge, discrete graphics ', '英特尔平台双桥独显正反面各': ' Intel platform, two bridges, discrete graphics, both sides each ',
    '英特尔双桥独显正反面各': ' Intel, two bridges, discrete graphics, both sides each ', '正反': ' both sides ',
    '集显': ' integrated graphics ', '集成显卡': ' integrated graphics ', '集成': ' integrated ', '集成一个': ' one integrated ',
    '集': ' integrated ', '独显': ' discrete graphics ', '独卡': ' discrete card ', '独': ' discrete ', '显卡': ' graphics card ',
    '显卡刷这个': ' graphics card, flash this ', '卡': ' card ', '独显能用': ' discrete graphics works ', '独显也通用': ' also fits discrete graphics ',
    '独显亮机': ' discrete graphics, displays ', '独显刷': ' discrete graphics, flashed ', '独显四显存': ' discrete graphics, four VRAM chips ',
    '显存': ' VRAM ', '四显存': ' four VRAM chips ', '两片显存': ' two VRAM chips ', '片显存': ' VRAM chips ', '颗显存': ' VRAM chips ',
    '板载': ' onboard ', '屏蔽板载内存': ' onboard RAM disabled ', '内存': ' RAM ', '代内存': '-gen RAM ', '内存贴纸': ' RAM sticker ',
    '贴纸': ' sticker ', '十一代': ' 11th-gen ', '四代': ' 4th-gen ', '代': '-gen ', '通用': ' generic ', '确定可通用': ' confirmed generic ',
    '版本': ' version ', '支持': ' supports ', '启动': ' boot ', '模式': ' mode ', '模式不能调': ' mode cannot be changed ',
    '充电': ' charge ', '待机': ' standby ', '在电池口': ' at the battery connector ', '序列号': ' serial number ',
    '有密码': ' has a password ', '有设密码': ' has a password set ', '密码': ' password ',

    # --- firmware dump notes: symptoms and results ---
    '亮机': ' boots with display ', '刷入亮机': ' flashed, boots with display ', '刷亮机': ' flash the display-OK image ',
    '可亮机': ' boots with display ', '测可亮机': ' tested, boots with display ', '刷测可亮机': ' flashed, tested, boots with display ',
    '一次亮机': ' displays first time ', '亮机很慢': ' slow to display ', '亮机快': ' quick to display ', '测亮机快': ' tested, quick to display ',
    '亮机保存': ' display OK, saved ', '秒亮机': '-second display ', '秒亮': ' instant display ', '确定能亮': ' confirmed to display ',
    '能亮机进系统': ' displays and enters the OS ', '不亮机': ' no display ', '不显': ' no display ', '不显的': ' no-display ',
    '不显坏': ' no display, bad ', '不显掉电': ' no display, power cuts out ', '不显循环跑内存': ' no display, loops at memory training ',
    '不显刷这个可亮': ' no display, flashing this brings display ', '不显的刷了这个还是不显': ' no display; still none after flashing this ',
    '有时不显': ' sometimes no display ', '有时不显的': ' sometimes no display ', '显示': ' display ', '显': ' display ',
    '可显': ' displays ', '可以显': ' displays ', '能显': ' displays ', '测能显': ' tested, displays ', '刷回去又可显': ' flashed back, displays again ',
    '刷回原来主板可以显示': ' displays when flashed back to the original board ', '开机显示慢刷': ' slow display at power-on, flash ',
    '开机不显示刷': ' no display at power-on, flash ', '开机瞬间显示有问题': ' display glitch at power-on ',
    '暗屏': ' dim screen ', '花屏': ' garbled screen ', '花屏死机': ' garbled screen, freezes ', '乱码': ' garbled ',
    '清屏': ' screen goes blank ', '进系统清屏': ' screen goes blank in the OS ', '刷了进系统清屏': ' after flashing, screen goes blank in the OS ',
    '集显进系统清屏刷这个': ' integrated graphics, screen blank in the OS, flash this ', '刷到清屏机器还是清屏': ' flashed on a blank-screen machine, still blank ',
    '进系统清屏故障可以尝试刷这个': ' for a blank screen in the OS, try flashing this ', '等很久会显示': ' shows after a long wait ',
    '但是卡死': ' but hangs ', '商用台式修复开机卡': ' business desktop, fixes boot hang at ', '标志': ' logo ',
    '死': ' dead ', '死机': ' freezes ', '也是死': ' also dead ', '蓝屏死机': ' blue screen, freezes ', '进系统蓝屏': ' blue screen in the OS ',
    '有时蓝屏': ' sometimes blue screen ', '打显卡驱动蓝屏重启': ' blue screen and restart on installing the graphics driver ',
    '独显解决开机硬盘不引导过滚动蓝屏': ' discrete graphics; fixes no boot from hard disk and scrolling blue screen ',
    '掉电': ' power cuts out ', '掉电一次': ' power cuts out once ', '分掉电': '-minute power cut ', '触发掉电': ' power cuts out on power-on ',
    '触发掉电不显': ' power cuts out on power-on, no display ', '跑内存掉电': ' power cuts out during memory training ',
    '掉电重启': ' power cut and restart ', '反复掉电重启': ' repeatedly loses power and restarts ',
    '别人说不定时掉电': ' reported random power cuts ', '换桥掉电': ' power cuts out after bridge replacement ',
    '刷了开机一样会掉电一次': ' after flashing, power still cuts out once at power-on ', '装大电池不掉电了': ' no power cut with the large battery ',
    '不装内存会触发掉电': ' powers off without RAM ', '检测不到内存也会掉电': ' powers off when RAM is not detected ',
    '出问题引起掉电': ' fault causing power-off ', '解决风扇狂转掉电问题': ' fixes fan at full speed and power cuts ',
    '触发不显': ' no display on power-on ', '有时不触发': ' sometimes does not power on ', '自动触发': ' powers on by itself ',
    '自动触发不出内存供电': ' powers on by itself, no RAM power ', '关机自动重启': ' restarts after shutdown ', '后重启': ' then restarts ',
    '关机慢': ' slow shutdown ', '开机': ' power-on ', '开机快': ' fast boot ', '解决开机慢': ' fixes slow boot ', '备份开机慢': ' backup, slow boot ',
    '解决开机电流': ' fixes power-on current ', '几': '-ish', '次进不去系统？': ' times, cannot enter the OS?', '进': ' enter ',
    '能进': ' can enter ', '测进系统': ' tested, enters the OS ', '进系统可以用': ' works in the OS ', '内存能进系统': ' RAM, enters the OS ',
    '要密码不引导': ' asks for a password, will not boot ', '测试貌似不引导': ' tested, seems not to boot ',
    '循环跑内存': ' loops at memory training ', '反复跑内存': ' repeatedly trains memory ', '不跑内存': ' does not train memory ',
    '不读内存': ' does not read RAM ', '内存复位': ' RAM reset ', '内存档': ' RAM, stuck at ', '档': ' stuck at ', '装': ' with ',
    '不出': ' no ', '有时不出': ' sometimes no ', '能出': ' gives ', '不出集显': ' no integrated graphics output ', '供电': ' power ',
    '显卡供电出来一下就掉': ' graphics power comes up then drops ', '翘起显卡供电': ' graphics power lifted ', '翘显卡电感可以显': ' lifting the graphics inductor gives display ',
    '没显卡驱动': ' no graphics driver ', '不认': ' does not detect ', '不认硬盘': ' does not detect the hard disk ',
    '不认硬盘的': ' not detecting the hard disk ', '触摸板不工作': ' touchpad not working ', '触摸不工作': ' touch not working ',
    '键盘触摸不工作': ' keyboard and touch not working ', '键盘工作异常': ' keyboard misbehaving ', '键盘灯能切换不显': ' keyboard light toggles, no display ',
    '声音': ' sound ', '声音不工作': ' sound not working ', '不充电': ' not charging ', '风扇会狂转': ' fan runs at full speed ',
    '这个刷了会风扇狂转': ' fan runs at full speed after flashing this ', '不能用': ' does not work ', '能用': ' works ',
    '不能改时间': ' cannot change the time ', '不过保护隔离': ' does not pass the protection isolation ', '忽略芯片错误': ' ignore chip errors ',
    '报错': ' reports errors ', '序列号报错': ' serial number error ', '可能会报错': ' may report errors ', '不报错': ' no errors ',
    '测没报错': ' tested, no errors ', '关掉工程模式报错后': ' after turning off the engineering-mode error ',
    '短': ' short ', '短路': ' short circuit ', '短路主板': ' shorted mainboard ', '桥短': ' bridge short ', '桥短路': ' bridge short circuit ',
    '屏线导致短路': ' screen cable caused a short ', '进水': ' water damage ', '风扇接口小板有进水': ' water in the fan connector board ',
    '清理后': ' after cleaning ', '后面加焊': ' later reflowed ', '加焊': ' reflowed ', '代换': ' substitute ', '可与': ' interchangeable with ',
    '换': ' replaced ', '给换成': ' swapped for ', '导': ' loaded ', '加个': ' added ', '报换': ' suggested replacing ',
    '修过一例': ' repaired one case of ', '修过一例电池死机换': ' repaired one battery-freeze case by replacing ', '修过': ' repaired ',
    '电池要一直按': ' battery: must hold ', '才能放电': ' to discharge ', '桥型号参考': ' bridge model for reference ',
    '故障': ' fault ', '通病': ' common fault ', '故障一样': ' same fault ', '一样故障': ' same fault ', '后面故障一样': ' later, same fault ',
    '官网故障依旧': ' official, fault persists ', '主板问题': ' mainboard problem ', '后问题': ' later problem ', '出问题': ' had problems ',
    '不确定问题': ' cause uncertain ', '刷': ' flash ', '刷了': ' flashed ', '刷机': ' flashed ', '刷机测试': ' flash test ',
    '刷官网': ' flashed the official ', '刷了官网': ' flashed the official ', '刷了官网一样': ' flashed the official, same ',
    '刷官网故障一样': ' flashed the official, same fault ', '刷了官网故障一样': ' flashed the official, same fault ',
    '后面刷官网故障一样': ' later flashed the official, same fault ', '刷了官网的还是一样': ' flashed the official, still the same ',
    '刷官网的好了': ' flashing the official fixed it ', '刷了故障一样': ' flashed, same fault ', '刷了不行': ' flashing did not help ',
    '刷这个即可': ' just flash this ', '刷这个可以': ' flashing this works ', '刷确定可以亮机': ' flashed, confirmed to display ',
    '刷其他不行再尝试这个': ' if others fail, try this ', '碰到个板子刷其他': ' on one board, flashing others ',
    '试过刷刷其他的不显': ' tried flashing others, no display ', '不确定放电好的还是刷': ' not sure whether discharging or flashing fixed it; flashed ',
    '别人刷过': ' flashed by someone else ', '别人动过': ' modified by someone else ', '别人修的乱七八糟不确定好坏': ' messed up by an earlier repair, not sure if good ',
    '解决': ' fixed ', '好了': ' fixed ', '可以好': ' can be fixed ', '可以解决': ' can fix ', '后可工作': ' after which it works ',
    '保存重启即可': ' just save and restart ', '按': ' press ', '用': ' using ', '用这个确定': ' confirmed with this ',
    '确定': ' confirmed ', '确认': ' confirmed ', '确定坏': ' confirmed bad ', '坏': ' bad ', '应该': ' should be ', '应该好的': ' should be good ',
    '经测是好的': ' tested good ', '测试好的': ' tested good ', '测试原机': ' tested original machine ', '亲测': ' personally tested ',
    '测试': ' tested ', '未测': ' untested ', '未测试': ' untested ', '未测试好坏': ' untested ', '待测': ' to be tested ',
    '具体没测': ' not tested in detail ', '具体其他问题还没测': ' other issues not yet tested ', '其他没测': ' other things not tested ',
    '不确定': ' not sure ', '不确定哪个': ' not sure which ', '不确定好坏': ' not sure if good ', '不知好坏': ' unknown if good ',
    '未知': ' unknown ', '未确认': ' unconfirmed ', '等几天拿出来测试没问题了': ' tested a few days later, no problem ',
    '也一样': ' also the same ', '前面少一点': ' a little missing at the start ', '之后的': ' after ', '到': ' to ',
    '有': ' has ', '带': ' with ', '不带': ' without ', '的': '', '成': '', '跑': ' runs ',

    # --- factory BOM lines ---
    '厚膜': 'thick film', '黑': 'black', '白': 'white', '藍': 'blue', '黃': 'yellow', '黑色': 'black', '白色': 'white',
    '黃色': 'yellow', '最後一碼為': 'last character is ', '特殊安規紙': 'special safety-rated insulating paper',
    '三耳扣鐵': 'three-ear clip, metal', '單耳扣鐵': 'single-ear clip, metal', '三耳扣塑膠': 'three-ear clip, plastic',
    '三耳扣塑膠背板': 'three-ear clip, plastic backplate', '三耳扣鐵件背板': 'three-ear clip, metal backplate',
    '跳線': 'jumper wire', '割線': 'cut wire', '請改用': 'use instead ', '各露': ' each end exposed ', '各裸露': ' each end stripped ',
    '條碼機用貼紙': 'barcode printer label', '一張': ' per sheet', '小張': ' small labels', '米': 'm', '單心線': 'single-core wire ',
    '時脈產生器': 'clock generator', '此料件不需': 'this part needs no ', '此為有鉛型號': 'this is the leaded part number',
    '實為': 'actually ', '內層': ' inner layer ', '元件': ' component ', '網號貼紙': 'network address label', '銘板': 'nameplate',
    '加長': 'extended ', '共': ' total ', '連片': '-up panel', '寬': ' wide',
    # approved-vendor (QVL) names
    '億光': 'Everlight', '台端': 'Tai Twun', '弼聖': 'Compupack', '廣迎': 'Kuang Ying', '瀚荃': 'CviLux', '安費諾': 'Amphenol',
    '西北台慶': 'Tai-Tech', '西北臺慶': 'Tai-Tech', '奇夢達': 'Qimonda', '雙鴻': 'Auras', '貝億德': 'Vette', '國格': 'KG',
    '致威': 'JVE', '喬訊': 'Chyao Shiunn', '宏泰': 'Hontech', '日騰': 'Ri-Teng', '連展': 'Advanced-Connectek (ACON)',
    '先進開發光': 'Advanced Optoelectronic Technology', '台灣航空電': 'JAE Taiwan', '昌先進': 'Ceratech',
    '上藝': 'Shang Yi', '嘉得隆': 'Jia De Long', '福華': 'Fu Hua', '千如': 'Chien Ju', '捷美美': 'Jie Mei Mei',
    '大智': 'Da Zhi', '亙台': 'Gen Tai', '榮藝': 'Rong Yi', '大煜': 'Da Yu', '瑞虹': 'Rui Hong', '精彥': 'Jing Yan',
    '榮益': 'Rong Yi', '惠貿': 'Hui Mao',                                       # romanized: no English name found

    # --- schematic and service-manual file names ---
    '和Ｂ液晶屏': ' and B LCD panel ', '和B液晶屏': ' and B LCD panel ', '液晶屏': ' LCD panel ', '采用': ' uses ',
    '机芯': ' chassis ', '彩电': ' colour TV ', '总线': ' bus ', '数据': ' data ',
}
