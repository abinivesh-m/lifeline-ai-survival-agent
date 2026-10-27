"""LIFELINE AI - generate the eight world locale files.

    python make_locales.py            # write locales/*.json
    python make_locales.py --check    # validate coverage only

Why eight: they cover the large majority of the ~3.5 billion people living in
low-infrastructure, flood-exposed towns, and they include the one that matters
personally - Tamil, the language this was built in.

    en  English      global responders, judges
    es  Spanish      Mexico, Central America, Philippines, 500M+
    fr  French       West Africa, Haiti, Sahel
    zh  Chinese      low-infra towns in China
    ar  Arabic       Syria, MENA, North Africa
    pt  Portuguese   Brazil
    sw  Swahili      Kenya, Tanzania, East Africa
    ta  Tamil        Kottur - the firsthand case

Every key must exist in every locale: an allocation warning that silently falls
back to English in Arabic is a safety failure, not a cosmetic one.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "locales"

LOCALES: dict[str, dict[str, str]] = {
    "en": {
        "language": "English",
        "native": "English",
        "dir": "ltr",
        "app.title": "LIFELINE AI",
        "app.subtitle": "Town survival agent",
        "app.tagline": "Built in Kottur. Works anywhere.",
        "lifegrid.blood": "BLOOD",
        "lifegrid.heart": "HEART",
        "lifegrid.lungs": "LUNGS",
        "lifegrid.organs": "ORGANS",
        "lifegrid.fuel": "diesel reserve",
        "lifegrid.runtime": "{hours} h runtime left",
        "lifegrid.feeder": "fed by the heart",
        "lifegrid.nowater": "no water, {hours} h",
        "route.blocked": "NH-544 km 42 blocked",
        "route.alt": "A* route {km} km",
        "route.saved": "{percent}% fuel saved",
        "alloc.title": "DIESEL ALLOCATION",
        "alloc.hospital": "hospital first",
        "alloc.pump": "water pump second",
        "alloc.total": "total {litres} L",
        "alloc.note": "fuel only - no medical advice",
        "credit.title": "CREDIT LEDGER",
        "credit.spent": "${spent} spent of ${ceiling} ceiling",
        "credit.alert": "alert at {percent}%",
        "gate.title": "Nothing is dispatched until a human decides",
        "gate.approve": "APPROVE",
        "gate.deny": "DENY",
        "gate.tier1": "0-5 min: human approval",
        "gate.tier2": "5-15 min: escalate to responders",
        "gate.tier3": "15-30 min: degraded auto-pilot, 50 L / 20 L",
        "gate.tier4": "over 30 min: community consensus, 2 of 3 leaders",
        "esc.tier2": "No reply yet. The hospital has {hours} h of diesel. Reply 1 to approve, 2 to deny.",
        "esc.tier3": "No human decision. Degraded autopilot: {hospital} L hospital, {pump} L pump, {reserve} L reserve kept.",
        "esc.tier4": "Community decision required: 3 shelter leaders, 2 of 3 must agree. {people} people waiting.",
        "esc.vote": "Vote on diesel dispatch: hospital {hospital} L, water pump {pump} L.",
        "evidence.landslide": "NH-544 km 42 landslide, road closed about 6 h",
        "evidence.people": "{people} people in shelters have no water",
        "world.scope": "3.5 billion people live in towns with this same cascade",
    },
    "es": {
        "language": "Spanish",
        "native": "Español",
        "dir": "ltr",
        "app.title": "LIFELINE AI",
        "app.subtitle": "Agente de supervivencia urbana",
        "app.tagline": "Creado en Kottur. Funciona en cualquier lugar.",
        "lifegrid.blood": "SANGRE",
        "lifegrid.heart": "CORAZÓN",
        "lifegrid.lungs": "PULMONES",
        "lifegrid.organs": "ÓRGANOS",
        "lifegrid.fuel": "reserva de diésel",
        "lifegrid.runtime": "{hours} h de autonomía restante",
        "lifegrid.feeder": "alimentado por el corazón",
        "lifegrid.nowater": "sin agua, {hours} h",
        "route.blocked": "NH-544 km 42 bloqueado",
        "route.alt": "Ruta A* {km} km",
        "route.saved": "{percent}% de combustible ahorrado",
        "alloc.title": "ASIGNACIÓN DE DIÉSEL",
        "alloc.hospital": "hospital primero",
        "alloc.pump": "bomba de agua después",
        "alloc.total": "total {litres} L",
        "alloc.note": "solo combustible: sin consejo médico",
        "credit.title": "REGISTRO DE CRÉDITO",
        "credit.spent": "${spent} gastado de un techo de ${ceiling}",
        "credit.alert": "alerta al {percent}%",
        "gate.title": "Nada se despacha hasta que una persona decida",
        "gate.approve": "APROBAR",
        "gate.deny": "RECHAZAR",
        "gate.tier1": "0-5 min: aprobación humana",
        "gate.tier2": "5-15 min: escalar a los socorristas",
        "gate.tier3": "15-30 min: piloto automático degradado, 50 L / 20 L",
        "gate.tier4": "más de 30 min: consenso comunitario, 2 de 3 líderes",
        "esc.tier2": "Aún sin respuesta. El hospital tiene {hours} h de diésel. Responda 1 para aprobar, 2 para rechazar.",
        "esc.tier3": "Sin decisión humana. Piloto automático degradado: {hospital} L hospital, {pump} L bomba, {reserve} L de reserva.",
        "esc.tier4": "Se requiere decisión comunitaria: 3 líderes de refugios, 2 de 3 deben aceptar. {people} personas esperan.",
        "esc.vote": "Voto sobre el envío de diésel: hospital {hospital} L, bomba de agua {pump} L.",
        "evidence.landslide": "NH-544 km 42 deslizamiento, carretera cerrada unas 6 h",
        "evidence.people": "{people} personas en refugios no tienen agua",
        "world.scope": "3.500 millones de personas viven en ciudades con esta misma cascada",
    },
    "fr": {
        "language": "French",
        "native": "Français",
        "dir": "ltr",
        "app.title": "LIFELINE AI",
        "app.subtitle": "Agent de survie urbaine",
        "app.tagline": "Conçu à Kottur. Fonctionne partout.",
        "lifegrid.blood": "SANG",
        "lifegrid.heart": "CŒUR",
        "lifegrid.lungs": "POUMONS",
        "lifegrid.organs": "ORGANES",
        "lifegrid.fuel": "réserve de gazole",
        "lifegrid.runtime": "{hours} h d'autonomie restante",
        "lifegrid.feeder": "alimenté par le cœur",
        "lifegrid.nowater": "sans eau, {hours} h",
        "route.blocked": "NH-544 km 42 bloqué",
        "route.alt": "Itinéraire A* {km} km",
        "route.saved": "{percent}% de carburant économisé",
        "alloc.title": "RÉPARTITION DU GAZOLE",
        "alloc.hospital": "hôpital d'abord",
        "alloc.pump": "pompe à eau ensuite",
        "alloc.total": "total {litres} L",
        "alloc.note": "carburant uniquement, aucun conseil médical",
        "credit.title": "REGISTRE DES CRÉDITS",
        "credit.spent": "${spent} dépensés sur un plafond de ${ceiling}",
        "credit.alert": "alerte à {percent}%",
        "gate.title": "Rien n'est expédié tant qu'un humain n'a pas décidé",
        "gate.approve": "APPROUVER",
        "gate.deny": "REFUSER",
        "gate.tier1": "0-5 min : approbation humaine",
        "gate.tier2": "5-15 min : escalade vers les secours",
        "gate.tier3": "15-30 min : pilote automatique dégradé, 50 L / 20 L",
        "gate.tier4": "plus de 30 min : consensus communautaire, 2 leaders sur 3",
        "esc.tier2": "Toujours sans réponse. L'hôpital a {hours} h de gazole. Répondez 1 pour approuver, 2 pour refuser.",
        "esc.tier3": "Aucune décision humaine. Pilote automatique dégradé : {hospital} L hôpital, {pump} L pompe, {reserve} L de réserve.",
        "esc.tier4": "Décision communautaire requise : 3 responsables d'abris, 2 sur 3 doivent accepter. {people} personnes attendent.",
        "esc.vote": "Vote sur l'envoi de gazole : hôpital {hospital} L, pompe à eau {pump} L.",
        "evidence.landslide": "NH-544 km 42 glissement de terrain, route fermée environ 6 h",
        "evidence.people": "{people} personnes dans les abris sont sans eau",
        "world.scope": "3,5 milliards de personnes vivent dans des villes connaissant cette même cascade",
    },
    "zh": {
        "language": "Chinese",
        "native": "中文",
        "dir": "ltr",
        "app.title": "LIFELINE AI",
        "app.subtitle": "城镇生存智能体",
        "app.tagline": "诞生于科图尔，适用于任何地方。",
        "lifegrid.blood": "血液",
        "lifegrid.heart": "心脏",
        "lifegrid.lungs": "肺",
        "lifegrid.organs": "器官",
        "lifegrid.fuel": "柴油储备",
        "lifegrid.runtime": "剩余 {hours} 小时运行",
        "lifegrid.feeder": "由心脏供电",
        "lifegrid.nowater": "无供水，{hours} 小时",
        "route.blocked": "NH-544 公里 42 处封锁",
        "route.alt": "A* 路线 {km} 公里",
        "route.saved": "节省 {percent}% 燃料",
        "alloc.title": "柴油分配",
        "alloc.hospital": "先保障医院",
        "alloc.pump": "其次供水泵",
        "alloc.total": "合计 {litres} 升",
        "alloc.note": "仅限燃料，不提供医疗建议",
        "credit.title": "额度台账",
        "credit.spent": "已用 ${spent}，上限 ${ceiling}",
        "credit.alert": "达到 {percent}% 时告警",
        "gate.title": "在人工批准之前不会派出任何物资",
        "gate.approve": "批准",
        "gate.deny": "拒绝",
        "gate.tier1": "0-5 分钟：人工审批",
        "gate.tier2": "5-15 分钟：升级至救援人员",
        "gate.tier3": "15-30 分钟：降级自动模式，50 升 / 20 升",
        "gate.tier4": "超过 30 分钟：社区共识，3 名负责人中 2 名同意",
        "esc.tier2": "尚未回复。医院仅剩 {hours} 小时柴油。回复 1 批准，回复 2 拒绝。",
        "esc.tier3": "无人工决策。降级自动模式：医院 {hospital} 升，水泵 {pump} 升，保留 {reserve} 升储备。",
        "esc.tier4": "需要社区决策：3 名避难所负责人中须有 2 名同意。{people} 人正在等待。",
        "esc.vote": "柴油派送表决：医院 {hospital} 升，水泵 {pump} 升。",
        "evidence.landslide": "NH-544 公里42山体滑坡，道路封闭约 6 小时",
        "evidence.people": "避难所内 {people} 人断水",
        "world.scope": "35 亿人生活在具有同样连锁风险的城镇",
    },
    "ar": {
        "language": "Arabic",
        "native": "العربية",
        "dir": "rtl",
        "app.title": "LIFELINE AI",
        "app.subtitle": "وكيل بقاء البلدة",
        "app.tagline": "بُني في كوتور. يعمل في أي مكان.",
        "lifegrid.blood": "الدم",
        "lifegrid.heart": "القلب",
        "lifegrid.lungs": "الرئتان",
        "lifegrid.organs": "الأعضاء",
        "lifegrid.fuel": "احتياطي الديزل",
        "lifegrid.runtime": "متبقٍ {hours} ساعات تشغيل",
        "lifegrid.feeder": "يُغذّى من القلب",
        "lifegrid.nowater": "بلا ماء، {hours} ساعات",
        "route.blocked": "NH-544 كم 42 مغلق",
        "route.alt": "مسار A* {km} كم",
        "route.saved": "توفير {percent}% من الوقود",
        "alloc.title": "توزيع الديزل",
        "alloc.hospital": "المستشفى أولاً",
        "alloc.pump": "مضخة المياه ثانياً",
        "alloc.total": "الإجمالي {litres} لتر",
        "alloc.note": "وقود فقط، لا نصائح طبية",
        "credit.title": "سجل الاعتمادات",
        "credit.spent": "أُنفق ${spent} من سقف ${ceiling}",
        "credit.alert": "تنبيه عند {percent}%",
        "gate.title": "لا يُرسل أي شيء حتى يقرر إنسان",
        "gate.approve": "موافقة",
        "gate.deny": "رفض",
        "gate.tier1": "0-5 دقائق: موافقة بشرية",
        "gate.tier2": "5-15 دقيقة: تصعيد إلى فرق الإغاثة",
        "gate.tier3": "15-30 دقيقة: طيار آلي مخفّض، 50 لتر / 20 لتر",
        "gate.tier4": "أكثر من 30 دقيقة: توافق مجتمعي، 2 من 3 قادة",
        "esc.tier2": "لا رد بعد. لدى المستشفى {hours} ساعات من الديزل. أرسل 1 للموافقة و2 للرفض.",
        "esc.tier3": "لا قرار بشري. طيار آلي مخفّض: {hospital} لتر للمستشفى، {pump} لتر للمضخة، مع الاحتفاظ بـ {reserve} لتر احتياطياً.",
        "esc.tier4": "مطلوب قرار مجتمعي: 3 من قادة الملاجئ، ويجب موافقة 2 من 3. {people} شخصاً في الانتظار.",
        "esc.vote": "تصويت على إرسال الديزل: المستشفى {hospital} لتر، مضخة المياه {pump} لتر.",
        "evidence.landslide": "NH-544 كم 42 انهيار أرضي، الطريق مغلق نحو 6 ساعات",
        "evidence.people": "{people} شخصاً في الملاجئ بلا ماء",
        "world.scope": "3.5 مليار شخص يعيشون في بلدات تواجه هذا التسلسل نفسه",
    },
    "pt": {
        "language": "Portuguese",
        "native": "Português",
        "dir": "ltr",
        "app.title": "LIFELINE AI",
        "app.subtitle": "Agente de sobrevivência urbana",
        "app.tagline": "Criado em Kottur. Funciona em qualquer lugar.",
        "lifegrid.blood": "SANGUE",
        "lifegrid.heart": "CORAÇÃO",
        "lifegrid.lungs": "PULMÕES",
        "lifegrid.organs": "ÓRGÃOS",
        "lifegrid.fuel": "reserva de diesel",
        "lifegrid.runtime": "{hours} h de autonomia restante",
        "lifegrid.feeder": "alimentado pelo coração",
        "lifegrid.nowater": "sem água, {hours} h",
        "route.blocked": "NH-544 km 42 bloqueado",
        "route.alt": "Rota A* {km} km",
        "route.saved": "{percent}% de combustível economizado",
        "alloc.title": "DISTRIBUIÇÃO DE DIESEL",
        "alloc.hospital": "hospital primeiro",
        "alloc.pump": "bomba de água depois",
        "alloc.total": "total {litres} L",
        "alloc.note": "apenas combustível, sem orientação médica",
        "credit.title": "REGISTRO DE CRÉDITOS",
        "credit.spent": "${spent} gastos de um teto de ${ceiling}",
        "credit.alert": "alerta em {percent}%",
        "gate.title": "Nada é despachado até que um humano decida",
        "gate.approve": "APROVAR",
        "gate.deny": "RECUSAR",
        "gate.tier1": "0-5 min: aprovação humana",
        "gate.tier2": "5-15 min: escalar para os socorristas",
        "gate.tier3": "15-30 min: piloto automático degradado, 50 L / 20 L",
        "gate.tier4": "mais de 30 min: consenso comunitário, 2 de 3 líderes",
        "esc.tier2": "Ainda sem resposta. O hospital tem {hours} h de diesel. Responda 1 para aprovar, 2 para recusar.",
        "esc.tier3": "Sem decisão humana. Piloto automático degradado: {hospital} L hospital, {pump} L bomba, {reserve} L de reserva.",
        "esc.tier4": "Decisão comunitária necessária: 3 líderes de abrigos, 2 de 3 devem concordar. {people} pessoas aguardam.",
        "esc.vote": "Votação sobre o envio de diesel: hospital {hospital} L, bomba de água {pump} L.",
        "evidence.landslide": "NH-544 km 42 deslizamento, estrada fechada cerca de 6 h",
        "evidence.people": "{people} pessoas em abrigos sem água",
        "world.scope": "3,5 bilhões de pessoas vivem em cidades com esta mesma cascata",
    },
    "sw": {
        "language": "Swahili",
        "native": "Kiswahili",
        "dir": "ltr",
        "app.title": "LIFELINE AI",
        "app.subtitle": "Wakala wa kunusuru mji",
        "app.tagline": "Imejengwa Kottur. Inafanya kazi popote.",
        "lifegrid.blood": "DAMU",
        "lifegrid.heart": "MOYO",
        "lifegrid.lungs": "MAPAFU",
        "lifegrid.organs": "VIUNGO",
        "lifegrid.fuel": "akiba ya dizeli",
        "lifegrid.runtime": "saa {hours} za uendeshaji zimesalia",
        "lifegrid.feeder": "hulishwa na moyo",
        "lifegrid.nowater": "hakuna maji, saa {hours}",
        "route.blocked": "NH-544 km 42 imefungwa",
        "route.alt": "Njia ya A* km {km}",
        "route.saved": "{percent}% mafuta yameokolewa",
        "alloc.title": "UGAWAJI WA DIZELI",
        "alloc.hospital": "hospitali kwanza",
        "alloc.pump": "pampu ya maji baadaye",
        "alloc.total": "jumla {litres} L",
        "alloc.note": "mafuta pekee, hakuna ushauri wa matibabu",
        "credit.title": "DAFTARI LA MIKOPO",
        "credit.spent": "${spent} zimetumika kati ya kikomo cha ${ceiling}",
        "credit.alert": "tahadhari kwa {percent}%",
        "gate.title": "Hakuna kinachotumwa hadi mtu aamue",
        "gate.approve": "IDHINISHA",
        "gate.deny": "KATAA",
        "gate.tier1": "dakika 0-5: idhini ya mtu",
        "gate.tier2": "dakika 5-15: kupandisha kwa waokoaji",
        "gate.tier3": "dakika 15-30: otomatiki iliyopunguzwa, 50 L / 20 L",
        "gate.tier4": "zaidi ya dakika 30: makubaliano ya jamii, 2 kati ya viongozi 3",
        "esc.tier2": "Hakuna jibu bado. Hospitali ina saa {hours} za dizeli. Jibu 1 kuidhinisha, 2 kukataa.",
        "esc.tier3": "Hakuna uamuzi wa mtu. Otomatiki iliyopunguzwa: {hospital} L hospitali, {pump} L pampu, {reserve} L akiba imehifadhiwa.",
        "esc.tier4": "Uamuzi wa jamii unahitajika: viongozi 3 wa makazi, 2 kati ya 3 wakubali. Watu {people} wanasubiri.",
        "esc.vote": "Kura kuhusu usafirishaji wa dizeli: hospitali {hospital} L, pampu ya maji {pump} L.",
        "evidence.landslide": "NH-544 km 42 maporomoko ya ardhi, barabara imefungwa takriban saa 6",
        "evidence.people": "watu {people} kwenye makazi hawana maji",
        "world.scope": "watu bilioni 3.5 wanaishi katika miji yenye mfululizo huu huo",
    },
    "ta": {
        "language": "Tamil",
        "native": "தமிழ்",
        "dir": "ltr",
        "app.title": "LIFELINE AI",
        "app.subtitle": "ஊர் பிழைப்பு முகவர்",
        "app.tagline": "கோட்டூரில் உருவானது. எங்கும் செயல்படும்.",
        "lifegrid.blood": "இரத்தம்",
        "lifegrid.heart": "இதயம்",
        "lifegrid.lungs": "நுரையீரல்",
        "lifegrid.organs": "உறுப்புகள்",
        "lifegrid.fuel": "டீசல் இருப்பு",
        "lifegrid.runtime": "{hours} மணி நேரம் இயக்கத்தில்",
        "lifegrid.feeder": "இதயத்தால் இயக்கப்படுகிறது",
        "lifegrid.nowater": "தண்ணீர் இல்லை, {hours} மணி",
        "route.blocked": "NH-544 கிமீ 42 மூடப்பட்டுள்ளது",
        "route.alt": "A* வழி {km} கிமீ",
        "route.saved": "{percent}% எரிபொருள் சேமிப்பு",
        "alloc.title": "டீசல் ஒதுக்கீடு",
        "alloc.hospital": "முதலில் மருத்துவமனை",
        "alloc.pump": "அடுத்து நீர் பம்ப்",
        "alloc.total": "மொத்தம் {litres} லிட்டர்",
        "alloc.note": "எரிபொருள் மட்டும், மருத்துவ ஆலோசனை இல்லை",
        "credit.title": "கடன் பதிவேடு",
        "credit.spent": "${spent} செலவு, ${ceiling} உச்ச வரம்பில்",
        "credit.alert": "{percent}% இல் எச்சரிக்கை",
        "gate.title": "மனிதர் முடிவெடுக்கும் வரை எதுவும் அனுப்பப்படாது",
        "gate.approve": "அனுமதி",
        "gate.deny": "மறு",
        "gate.tier1": "0-5 நிமிடம்: மனித அனுமதி",
        "gate.tier2": "5-15 நிமிடம்: மீட்புக் குழுவுக்கு அனுப்பு",
        "gate.tier3": "15-30 நிமிடம்: தானியங்கி பயன்முறை, 50 லி / 20 லி",
        "gate.tier4": "30 நிமிடத்திற்கு மேல்: சமூக ஒருமித்த முடிவு, 3 தலைவர்களில் 2",
        "esc.tier2": "இன்னும் பதில் இல்லை. மருத்துவமனையில் {hours} மணி நேர டீசல் மட்டுமே உள்ளது. அனுமதிக்க 1, மறுக்க 2 அனுப்புங்கள்.",
        "esc.tier3": "மனித முடிவு இல்லை. தானியங்கி பயன்முறை: மருத்துவமனை {hospital} லி, பம்ப் {pump} லி, {reserve} லி இருப்பு தக்கவைக்கப்பட்டது.",
        "esc.tier4": "சமூக முடிவு தேவை: 3 தங்குமிடத் தலைவர்களில் 2 பேர் ஒப்புக்கொள்ள வேண்டும். {people} பேர் காத்திருக்கின்றனர்.",
        "esc.vote": "டீசல் அனுப்பீட்டு வாக்கெடுப்பு: மருத்துவமனை {hospital} லி, நீர் பம்ப் {pump} லி.",
        "evidence.landslide": "NH-544 கிமீ 42 நிலச்சரிவு, சாலை சுமார் 6 மணி நேரம் மூடல்",
        "evidence.people": "தங்குமிடங்களில் {people} பேருக்கு தண்ணீர் இல்லை",
        "world.scope": "இதே தொடர் விளைவைக் கொண்ட நகரங்களில் 350 கோடி மக்கள் வாழ்கிறார்கள்",
    },
}


def check() -> list[str]:
    problems: list[str] = []
    if "en" not in LOCALES:
        problems.append("missing baseline locale 'en'")
        return problems
    baseline = set(LOCALES["en"])
    for code, table in LOCALES.items():
        missing = baseline - set(table)
        extra = set(table) - baseline
        if missing:
            problems.append(f"{code}: missing {len(missing)} key(s): {sorted(missing)[:5]}")
        if extra:
            problems.append(f"{code}: {len(extra)} unknown key(s): {sorted(extra)[:5]}")
        for key, value in table.items():
            if not isinstance(value, str) or not value.strip():
                problems.append(f"{code}: {key} is empty")
    return problems


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="generate world locales")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    problems = check()
    OUT.mkdir(exist_ok=True)
    for code, table in LOCALES.items():
        (OUT / f"{code}.json").write_text(
            json.dumps(table, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    payload = {
        "locales": [
            {"code": c, "language": t["language"], "native": t["native"], "dir": t["dir"]}
            for c, t in LOCALES.items()
        ],
        "count": len(LOCALES),
        "keys_per_locale": len(LOCALES["en"]),
    }
    (OUT / "index.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"wrote {len(LOCALES)} locales to {OUT.name}/  "
          f"({payload['keys_per_locale']} keys each)")
    print("  " + "  ".join(f"{c}:{t['native']}" for c, t in LOCALES.items()))

    if problems:
        print("\nCOVERAGE PROBLEMS")
        for problem in problems:
            print("  -", problem)
        return 1
    print("\ncoverage OK - every key present in every locale")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
