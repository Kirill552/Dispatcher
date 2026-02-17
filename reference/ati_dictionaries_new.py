# -*- coding: utf-8 -*-
"""
АТИ СЛОВАРИ - Автоматически сгенерированные справочники для АТИ API v1.0
Используется для сопоставления пользовательского ввода с корректными ID АТИ
"""

# =============================================================================
# ТИПЫ КУЗОВОВ (carTypes)
# =============================================================================

CAR_TYPES = [
    {
        "Attribs": 4,
        "Position": 50,
        "TypeId": 100,
        "StringifiedTypeId": "2",
        "NameEng": "container",
        "ShortName": "конт.",
        "ShortNameEng": "cont",
        "Id": 2,
        "Id2": "15da7543-9812-e411-8e11-00259038ec34",
        "Name": "контейнер"
    },
    {
        "Attribs": 4,
        "Position": 20,
        "TypeId": 200,
        "StringifiedTypeId": "1",
        "NameEng": "tent truck",
        "ShortName": "тент.",
        "ShortNameEng": "tent",
        "Id": 1,
        "Id2": "14da7543-9812-e411-8e11-00259038ec34",
        "Name": "тентованный"
    },
    {
        "Attribs": 5,
        "Position": 85,
        "TypeId": 300,
        "StringifiedTypeId": "4",
        "NameEng": "refrigerator",
        "ShortName": "реф.",
        "ShortNameEng": "reef",
        "Id": 4,
        "Id2": "16da7543-9812-e411-8e11-00259038ec34",
        "Name": "рефрижератор"
    },
    {
        "Attribs": 5,
        "Position": 87,
        "TypeId": 310,
        "StringifiedTypeId": "281474976710656",
        "NameEng": "bulkhead refr.",
        "ShortName": "реф.с перег.",
        "ShortNameEng": "bulk. refr.",
        "Id": 281474976710656,
        "Id2": "05c8927b-8919-e511-8fc8-002590e45781",
        "Name": "реф. с перегородкой"
    },
    {
        "Attribs": 5,
        "Position": 86,
        "TypeId": 312,
        "StringifiedTypeId": "562949953421312",
        "NameEng": "refrigerator mult.",
        "ShortName": "реф.мульт.",
        "ShortNameEng": "ref.mult.",
        "Id": 562949953421312,
        "Id2": "e3e45ac3-8919-e511-8fc8-002590e45781",
        "Name": "реф. мультирежимный"
    },
    {
        "Attribs": 7,
        "Position": 75,
        "TypeId": 400,
        "StringifiedTypeId": "8",
        "NameEng": "isothermal",
        "ShortName": "изотерм",
        "ShortNameEng": "isotherm",
        "Id": 8,
        "Id2": "17da7543-9812-e411-8e11-00259038ec34",
        "Name": "изотермический"
    },
    {
        "Attribs": 4,
        "Position": 60,
        "TypeId": 500,
        "StringifiedTypeId": "16",
        "NameEng": "van",
        "ShortName": "фург.",
        "ShortNameEng": "van",
        "Id": 16,
        "Id2": "18da7543-9812-e411-8e11-00259038ec34",
        "Name": "фургон"
    },
    {
        "Attribs": 0,
        "Position": 286,
        "TypeId": 600,
        "StringifiedTypeId": "32",
        "NameEng": "microbus",
        "ShortName": "микр.",
        "ShortNameEng": "mbus",
        "Id": 32,
        "Id2": "19da7543-9812-e411-8e11-00259038ec34",
        "Name": "микроавтобус"
    },
    {
        "Attribs": 0,
        "Position": 70,
        "TypeId": 700,
        "StringifiedTypeId": "64",
        "NameEng": "all-metal",
        "ShortName": "цмет.",
        "ShortNameEng": "metal",
        "Id": 64,
        "Id2": "1ada7543-9812-e411-8e11-00259038ec34",
        "Name": "цельнометалл."
    },
    {
        "Attribs": 12,
        "Position": 100,
        "TypeId": 1100,
        "StringifiedTypeId": "128",
        "NameEng": "flatbed",
        "ShortName": "борт.",
        "ShortNameEng": "flat.",
        "Id": 128,
        "Id2": "1cda7543-9812-e411-8e11-00259038ec34",
        "Name": "бортовой"
    },
    {
        "Attribs": 4,
        "Position": 120,
        "TypeId": 1150,
        "StringifiedTypeId": "1024",
        "NameEng": "opentop",
        "ShortName": "откр.конт.",
        "ShortNameEng": "opn.top",
        "Id": 1024,
        "Id2": "1fda7543-9812-e411-8e11-00259038ec34",
        "Name": "открытый конт."
    },
    {
        "Attribs": 8,
        "Position": 295,
        "TypeId": 1170,
        "StringifiedTypeId": "68719476736",
        "NameEng": "pickup",
        "ShortName": "пикап",
        "ShortNameEng": "pick",
        "Id": 68719476736,
        "Id2": "39da7543-9812-e411-8e11-00259038ec34",
        "Name": "пикап"
    },
    {
        "Attribs": 4,
        "Position": 130,
        "TypeId": 1200,
        "StringifiedTypeId": "4096",
        "NameEng": "dump truck",
        "ShortName": "ссвл.",
        "ShortNameEng": "dump",
        "Id": 4096,
        "Id2": "21da7543-9812-e411-8e11-00259038ec34",
        "Name": "самосвал"
    },
    {
        "Attribs": 0,
        "Position": 265,
        "TypeId": 1250,
        "StringifiedTypeId": "4194304",
        "NameEng": "furage tuck",
        "ShortName": "корм.",
        "ShortNameEng": "furag",
        "Id": 4194304,
        "Id2": "2bda7543-9812-e411-8e11-00259038ec34",
        "Name": "кормовоз"
    },
    {
        "Attribs": 0,
        "Position": 255,
        "TypeId": 1280,
        "StringifiedTypeId": "137438953472",
        "NameEng": "horse truck",
        "ShortName": "кони.",
        "ShortNameEng": "hors.",
        "Id": 137438953472,
        "Id2": "3ada7543-9812-e411-8e11-00259038ec34",
        "Name": "коневоз"
    },
    {
        "Attribs": 12,
        "Position": 260,
        "TypeId": 1300,
        "StringifiedTypeId": "2097152",
        "NameEng": "container trail.",
        "ShortName": "конт-воз",
        "ShortNameEng": "trail",
        "Id": 2097152,
        "Id2": "2ada7543-9812-e411-8e11-00259038ec34",
        "Name": "контейнеровоз"
    },
    {
        "Attribs": 8,
        "Position": 283,
        "TypeId": 1350,
        "StringifiedTypeId": "256",
        "NameEng": "manipulator",
        "ShortName": "манип",
        "ShortNameEng": "manip",
        "Id": 256,
        "Id2": "1dda7543-9812-e411-8e11-00259038ec34",
        "Name": "манипулятор"
    },
    {
        "Attribs": 12,
        "Position": 123,
        "TypeId": 1355,
        "StringifiedTypeId": "70368744177664",
        "NameEng": "opentrailer",
        "ShortName": "безборт.",
        "ShortNameEng": "opn.tr.",
        "Id": 70368744177664,
        "Id2": "ac5fdced-8644-e411-8e11-00259038ec34",
        "Name": "площадка без бортов"
    },
    {
        "Attribs": 8,
        "Position": 140,
        "TypeId": 1400,
        "StringifiedTypeId": "8192",
        "NameEng": "barge",
        "ShortName": "шал.",
        "ShortNameEng": "barg",
        "Id": 8192,
        "Id2": "22da7543-9812-e411-8e11-00259038ec34",
        "Name": "шаланда"
    },
    {
        "Attribs": 6,
        "Position": 180,
        "TypeId": 5000,
        "StringifiedTypeId": "18726594281984",
        "NameEng": "outsize",
        "ShortName": "негаб.",
        "ShortNameEng": "outs",
        "Id": 18726594281984,
        "Id2": "3eda7543-9812-e411-8e11-00259038ec34",
        "Name": "негабарит"
    },
    {
        "Attribs": 8,
        "Position": 270,
        "TypeId": 10000,
        "StringifiedTypeId": "8388608",
        "NameEng": "crane",
        "ShortName": "кран",
        "ShortNameEng": "crane",
        "Id": 8388608,
        "Id2": "2cda7543-9812-e411-8e11-00259038ec34",
        "Name": "кран"
    },
    {
        "Attribs": 8,
        "Position": 220,
        "TypeId": 10100,
        "StringifiedTypeId": "131072",
        "NameEng": "auto carrier",
        "ShortName": "автт.",
        "ShortNameEng": "autc.",
        "Id": 131072,
        "Id2": "26da7543-9812-e411-8e11-00259038ec34",
        "Name": "автотранспортер"
    },
    {
        "Attribs": 4,
        "Position": 370,
        "TypeId": 10200,
        "StringifiedTypeId": "8589934592",
        "NameEng": "tanker truck",
        "ShortName": "автоцист.",
        "ShortNameEng": "tanker truck.",
        "Id": 8589934592,
        "Id2": "36da7543-9812-e411-8e11-00259038ec34",
        "Name": "автоцистерна"
    },
    {
        "Attribs": 8,
        "Position": 280,
        "TypeId": 10300,
        "StringifiedTypeId": "16777216",
        "NameEng": "timber truck",
        "ShortName": "лесв.",
        "ShortNameEng": "timb",
        "Id": 16777216,
        "Id2": "2dda7543-9812-e411-8e11-00259038ec34",
        "Name": "лесовоз"
    },
    {
        "Attribs": 12,
        "Position": 294,
        "TypeId": 10320,
        "StringifiedTypeId": "2048",
        "NameEng": "panels truck",
        "ShortName": "панв.",
        "ShortNameEng": "panel",
        "Id": 2048,
        "Id2": "20da7543-9812-e411-8e11-00259038ec34",
        "Name": "панелевоз"
    },
    {
        "Attribs": 8,
        "Position": 282,
        "TypeId": 10330,
        "StringifiedTypeId": "1125899906842624",
        "NameEng": "scrap truck",
        "ShortName": "лом.",
        "ShortNameEng": "scrap",
        "Id": 1125899906842624,
        "Id2": "4c6e7a44-6443-e611-b00c-002590e45781",
        "Name": "ломовоз"
    },
    {
        "Attribs": 12,
        "Position": 350,
        "TypeId": 10350,
        "StringifiedTypeId": "1073741824",
        "NameEng": "pipe truck",
        "ShortName": "труб.",
        "ShortNameEng": "pipe",
        "Id": 1073741824,
        "Id2": "33da7543-9812-e411-8e11-00259038ec34",
        "Name": "трубовоз"
    },
    {
        "Attribs": 8,
        "Position": 310,
        "TypeId": 10400,
        "StringifiedTypeId": "67108864",
        "NameEng": "tractor",
        "ShortName": "тягач",
        "ShortNameEng": "tract",
        "Id": 67108864,
        "Id2": "2fda7543-9812-e411-8e11-00259038ec34",
        "Name": "седельный тягач"
    },
    {
        "Attribs": 8,
        "Position": 185,
        "TypeId": 10500,
        "StringifiedTypeId": "512",
        "NameEng": "dolly",
        "ShortName": "рамн.",
        "ShortNameEng": "dolly",
        "Id": 512,
        "Id2": "1eda7543-9812-e411-8e11-00259038ec34",
        "Name": "низкорамный"
    },
    {
        "Attribs": 8,
        "Position": 190,
        "TypeId": 10550,
        "StringifiedTypeId": "34359738368",
        "NameEng": "dolly plat.",
        "ShortName": "нпл.",
        "ShortNameEng": "dpl",
        "Id": 34359738368,
        "Id2": "38da7543-9812-e411-8e11-00259038ec34",
        "Name": "низкорам.платф."
    },
    {
        "Attribs": 8,
        "Position": 195,
        "TypeId": 10570,
        "StringifiedTypeId": "1099511627776",
        "NameEng": "adjustable",
        "ShortName": "телскп.",
        "ShortNameEng": "adj.",
        "Id": 1099511627776,
        "Id2": "3dda7543-9812-e411-8e11-00259038ec34",
        "Name": "телескопический"
    },
    {
        "Attribs": 1,
        "Position": 240,
        "TypeId": 10600,
        "StringifiedTypeId": "524288",
        "NameEng": "gas",
        "ShortName": "газ.",
        "ShortNameEng": "gas",
        "Id": 524288,
        "Id2": "28da7543-9812-e411-8e11-00259038ec34",
        "Name": "газовоз"
    },
    {
        "Attribs": 8,
        "Position": 200,
        "TypeId": 10700,
        "StringifiedTypeId": "536870912",
        "NameEng": "tral",
        "ShortName": "трал",
        "ShortNameEng": "tral",
        "Id": 536870912,
        "Id2": "32da7543-9812-e411-8e11-00259038ec34",
        "Name": "трал"
    },
    {
        "Attribs": 4,
        "Position": 205,
        "TypeId": 10800,
        "StringifiedTypeId": "16384",
        "NameEng": "bus",
        "ShortName": "авт.",
        "ShortNameEng": "bus",
        "Id": 16384,
        "Id2": "23da7543-9812-e411-8e11-00259038ec34",
        "Name": "автобус"
    },
    {
        "Attribs": 0,
        "Position": 320,
        "TypeId": 10900,
        "StringifiedTypeId": "134217728",
        "NameEng": "cattle",
        "ShortName": "скот.",
        "ShortNameEng": "cattl",
        "Id": 134217728,
        "Id2": "30da7543-9812-e411-8e11-00259038ec34",
        "Name": "скотовоз"
    },
    {
        "Attribs": 0,
        "Position": 330,
        "TypeId": 10950,
        "StringifiedTypeId": "268435456",
        "NameEng": "innloader",
        "ShortName": "сткл.",
        "ShortNameEng": "innl",
        "Id": 268435456,
        "Id2": "31da7543-9812-e411-8e11-00259038ec34",
        "Name": "стекловоз"
    },
    {
        "Attribs": 6,
        "Position": 90,
        "TypeId": 20000,
        "StringifiedTypeId": "70368744191104",
        "NameEng": "all open",
        "ShortName": "откр.",
        "ShortNameEng": "open",
        "Id": 70368744191104,
        "Id2": "44da7543-9812-e411-8e11-00259038ec34",
        "Name": "все открытые"
    },
    {
        "Attribs": 0,
        "Position": 360,
        "TypeId": 20100,
        "StringifiedTypeId": "2147483648",
        "NameEng": "cement truck",
        "ShortName": "цем.",
        "ShortNameEng": "cemnt",
        "Id": 2147483648,
        "Id2": "34da7543-9812-e411-8e11-00259038ec34",
        "Name": "цементовоз"
    },
    {
        "Attribs": 0,
        "Position": 375,
        "TypeId": 20150,
        "StringifiedTypeId": "4294967296",
        "NameEng": "chip truck",
        "ShortName": "щеп.",
        "ShortNameEng": "chip",
        "Id": 4294967296,
        "Id2": "35da7543-9812-e411-8e11-00259038ec34",
        "Name": "щеповоз"
    },
    {
        "Attribs": 0,
        "Position": 290,
        "TypeId": 20200,
        "StringifiedTypeId": "33554432",
        "NameEng": "flour truck",
        "ShortName": "мук.",
        "ShortNameEng": "flour",
        "Id": 33554432,
        "Id2": "2eda7543-9812-e411-8e11-00259038ec34",
        "Name": "муковоз"
    },
    {
        "Attribs": 8,
        "Position": 210,
        "TypeId": 20300,
        "StringifiedTypeId": "32768",
        "NameEng": "Autocart",
        "ShortName": "автв.",
        "ShortNameEng": "autcr",
        "Id": 32768,
        "Id2": "24da7543-9812-e411-8e11-00259038ec34",
        "Name": "автовоз"
    },
    {
        "Attribs": 8,
        "Position": 215,
        "TypeId": 20350,
        "StringifiedTypeId": "65536",
        "NameEng": "autotower",
        "ShortName": "вышк.",
        "ShortNameEng": "towr.",
        "Id": 65536,
        "Id2": "25da7543-9812-e411-8e11-00259038ec34",
        "Name": "автовышка"
    },
    {
        "Attribs": 0,
        "Position": 230,
        "TypeId": 20500,
        "StringifiedTypeId": "262144",
        "NameEng": "сoncrete truck",
        "ShortName": "бет.",
        "ShortNameEng": "conc.",
        "Id": 262144,
        "Id2": "27da7543-9812-e411-8e11-00259038ec34",
        "Name": "бетоновоз"
    },
    {
        "Attribs": 0,
        "Position": 232,
        "TypeId": 20550,
        "StringifiedTypeId": "2199023255552",
        "NameEng": "bitumen truck",
        "ShortName": "битум",
        "ShortNameEng": "bitum",
        "Id": 2199023255552,
        "Id2": "3fda7543-9812-e411-8e11-00259038ec34",
        "Name": "битумовоз"
    },
    {
        "Attribs": 8,
        "Position": 203,
        "TypeId": 20560,
        "StringifiedTypeId": "17592186044416",
        "NameEng": "beam truck(ngb)",
        "ShortName": "балк.",
        "ShortNameEng": "beam",
        "Id": 17592186044416,
        "Id2": "42da7543-9812-e411-8e11-00259038ec34",
        "Name": "балковоз(негабарит)"
    },
    {
        "Attribs": 8,
        "Position": 400,
        "TypeId": 20600,
        "StringifiedTypeId": "17179869184",
        "NameEng": "wrecker",
        "ShortName": "эвак.",
        "ShortNameEng": "wreck",
        "Id": 17179869184,
        "Id2": "37da7543-9812-e411-8e11-00259038ec34",
        "Name": "эвакуатор"
    },
    {
        "Attribs": 4,
        "Position": 235,
        "TypeId": 20700,
        "StringifiedTypeId": "274877906944",
        "NameEng": "fuel tank",
        "ShortName": "бенз.",
        "ShortNameEng": "fuel.",
        "Id": 274877906944,
        "Id2": "3bda7543-9812-e411-8e11-00259038ec34",
        "Name": "бензовоз"
    },
    {
        "Attribs": 0,
        "Position": 237,
        "TypeId": 20750,
        "StringifiedTypeId": "549755813888",
        "NameEng": "off-roader",
        "ShortName": "вздхд.",
        "ShortNameEng": "off.rd.",
        "Id": 549755813888,
        "Id2": "3cda7543-9812-e411-8e11-00259038ec34",
        "Name": "вездеход"
    },
    {
        "Attribs": 5,
        "Position": 89,
        "TypeId": 20800,
        "StringifiedTypeId": "4398046511104",
        "NameEng": "meat rails ref.",
        "ShortName": "р-туш.",
        "ShortNameEng": "meat",
        "Id": 4398046511104,
        "Id2": "40da7543-9812-e411-8e11-00259038ec34",
        "Name": "реф.-тушевоз"
    },
    {
        "Attribs": 8,
        "Position": 297,
        "TypeId": 20850,
        "StringifiedTypeId": "8796093022208",
        "NameEng": "pyramid",
        "ShortName": "пирам.",
        "ShortNameEng": "pyra",
        "Id": 8796093022208,
        "Id2": "41da7543-9812-e411-8e11-00259038ec34",
        "Name": "пирамида"
    },
    {
        "Attribs": 8,
        "Position": 296,
        "TypeId": 20860,
        "StringifiedTypeId": "140737488355328",
        "NameEng": "ripetruck",
        "ShortName": "пухта",
        "ShortNameEng": "ripe",
        "Id": 140737488355328,
        "Id2": "29a93fd6-d414-e511-8fc8-002590e45781",
        "Name": "пухтовоз"
    },
    {
        "Attribs": 8,
        "Position": 300,
        "TypeId": 20870,
        "StringifiedTypeId": "35184372088832",
        "NameEng": "roll truck",
        "ShortName": "рул.",
        "ShortNameEng": "roll",
        "Id": 35184372088832,
        "Id2": "43da7543-9812-e411-8e11-00259038ec34",
        "Name": "рулоновоз"
    },
    {
        "Attribs": 6,
        "Position": 10,
        "TypeId": 30000,
        "StringifiedTypeId": "91",
        "NameEng": "all closed+isotherm",
        "ShortName": "закр.+терм.",
        "ShortNameEng": "closed+therm.",
        "Id": 91,
        "Id2": "1bda7543-9812-e411-8e11-00259038ec34",
        "Name": "все закр.+изотерм"
    },
    {
        "Attribs": 0,
        "Position": 250,
        "TypeId": 40000,
        "StringifiedTypeId": "1048576",
        "NameEng": "grain truck",
        "ShortName": "зерн.",
        "ShortNameEng": "grain",
        "Id": 1048576,
        "Id2": "29da7543-9812-e411-8e11-00259038ec34",
        "Name": "зерновоз"
    },
    {
        "Attribs": 6,
        "Position": 80,
        "TypeId": 50000,
        "StringifiedTypeId": "844424930131980",
        "NameEng": "ref.+isotherm",
        "ShortName": "реф.+терм.",
        "ShortNameEng": "ref.+therm.",
        "Id": 844424930131980,
        "Id2": "20c5e16d-f460-e411-a701-00259038ec34",
        "Name": "реф.+изотерм"
    },
    {
        "Attribs": 0,
        "Position": 410,
        "TypeId": 55000,
        "StringifiedTypeId": "2251799813685248",
        "NameEng": "dual-purpose",
        "ShortName": "грузпас.",
        "ShortNameEng": "dual-purpose",
        "Id": 2251799813685248,
        "Id2": "b3559c20-18dc-4ec0-90fd-bdd7187c3491",
        "Name": "грузопассажирский"
    },
    {
        "Attribs": 0,
        "Position": 420,
        "TypeId": 55500,
        "StringifiedTypeId": "4503599627370496",
        "NameEng": "klyushkovoz",
        "ShortName": "клюшк.",
        "ShortNameEng": "klyush.",
        "Id": 4503599627370496,
        "Id2": "9e39eefe-6799-e811-bb96-0cc47af30c1b",
        "Name": "клюшковоз"
    },
    {
        "Attribs": 0,
        "Position": 430,
        "TypeId": 56000,
        "StringifiedTypeId": "9007199254740992",
        "NameEng": "garbage truck",
        "ShortName": "мусор.",
        "ShortNameEng": "garb.",
        "Id": 9007199254740992,
        "Id2": "a0ac9015-40ee-e811-825a-3497f6db722c",
        "Name": "мусоровоз"
    },
    {
        "Attribs": 0,
        "Position": 440,
        "TypeId": 56500,
        "StringifiedTypeId": "18014398509481984",
        "NameEng": "jumbo",
        "ShortName": "jumbo",
        "ShortNameEng": "jumbo",
        "Id": 18014398509481984,
        "Id2": "34b02d72-050b-4525-a674-6df506dc67b5",
        "Name": "jumbo"
    },
    {
        "Attribs": 0,
        "Position": 450,
        "TypeId": 57000,
        "StringifiedTypeId": "36028797018963968",
        "NameEng": "20' tank-container",
        "ShortName": "20' танк-конт.",
        "ShortNameEng": "20' tank-cont.",
        "Id": 36028797018963968,
        "Id2": "6425c3bd-0aaa-4ccd-bd09-97d7a717f601",
        "Name": "20' танк-контейнер"
    },
    {
        "Attribs": 0,
        "Position": 460,
        "TypeId": 57500,
        "StringifiedTypeId": "72057594037927936",
        "NameEng": "40' tank-container",
        "ShortName": "40' танк-конт.",
        "ShortNameEng": "40' tank-cont.",
        "Id": 72057594037927936,
        "Id2": "fe5f8bfd-1909-4bf2-b81b-b174eeebc3da",
        "Name": "40' танк-контейнер"
    },
    {
        "Attribs": 0,
        "Position": 470,
        "TypeId": 58000,
        "StringifiedTypeId": "144115188075855872",
        "NameEng": "mega",
        "ShortName": "мега",
        "ShortNameEng": "mega",
        "Id": 144115188075855872,
        "Id2": "bf022a10-73d6-4775-a6e2-db5287ed9b3a",
        "Name": "мега фура"
    },
    {
        "Attribs": 0,
        "Position": 480,
        "TypeId": 58500,
        "StringifiedTypeId": "288230376151711744",
        "NameEng": "doppelstock",
        "ShortName": "допельшток",
        "ShortNameEng": "doppelstock",
        "Id": 288230376151711744,
        "Id2": "b0f3b038-6b5c-4c0c-a78e-b5433c4956d4",
        "Name": "допельшток"
    },
    {
        "Attribs": 0,
        "Position": 490,
        "TypeId": 59000,
        "StringifiedTypeId": "576460752303423488",
        "NameEng": "Sliding semi-trailer 20'/40'",
        "ShortName": "Раздв. полу. 20'/40'",
        "ShortNameEng": "Slid. semi. 20'/40'",
        "Id": 576460752303423488,
        "Id2": "5fa4d607-be78-ee11-bbc5-0cc47af31075",
        "Name": "Раздвижной полуприцеп 20'/40'"
    }
]

# =============================================================================
# ТИПЫ ГРУЗОВ (cargoTypes)
# =============================================================================

CARGO_TYPES = [
    {
        "NameEng": "Car(s)",
        "Id": 111,
        "Id2": "697df7e1-14d6-e811-bb97-0cc47af30c1b",
        "Name": "Автомобиль(ли)"
    },
    {
        "NameEng": "Autotrunks",
        "Id": 1,
        "Id2": "14bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Автошины"
    },
    {
        "NameEng": "Alcoholic drinks",
        "Id": 2,
        "Id2": "15bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Алкогольные напитки"
    },
    {
        "NameEng": "Reinforcement",
        "Id": 98,
        "Id2": "72bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Арматура"
    },
    {
        "NameEng": "Train bolster",
        "Id": 112,
        "Id2": "7c105add-3061-413a-9393-3d7c41cbbf39",
        "Name": "Балки надрессорные"
    },
    {
        "NameEng": "Soft drinks",
        "Id": 3,
        "Id2": "16bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Безалкогольные напитки"
    },
    {
        "NameEng": "Train side frame",
        "Id": 114,
        "Id2": "bea72196-06b8-4cbf-bc93-764cf803f3e3",
        "Name": "Боковая рама"
    },
    {
        "NameEng": "Paper",
        "Id": 4,
        "Id2": "17bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Бумага"
    },
    {
        "NameEng": "Home appliances",
        "Id": 5,
        "Id2": "18bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Бытовая техника"
    },
    {
        "NameEng": "Household chemical goods",
        "Id": 82,
        "Id2": "62bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Бытовая химия"
    },
    {
        "NameEng": "Lining",
        "Id": 87,
        "Id2": "67bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Вагонка"
    },
    {
        "NameEng": "Gas-silicate idlers",
        "Id": 97,
        "Id2": "71bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Газосиликатные блоки"
    },
    {
        "NameEng": "Gypsum",
        "Id": 96,
        "Id2": "70bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Гипс"
    },
    {
        "NameEng": "Corrugated cardboard",
        "Id": 68,
        "Id2": "55bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Гофрокартон"
    },
    {
        "NameEng": "Mushrooms",
        "Id": 6,
        "Id2": "19bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Грибы"
    },
    {
        "NameEng": "Doors",
        "Id": 101,
        "Id2": "74bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Двери"
    },
    {
        "NameEng": "WFP",
        "Id": 83,
        "Id2": "63bf285b-9812-e411-8e11-00259038ec34",
        "Name": "ДВП"
    },
    {
        "NameEng": "House moving",
        "Id": 102,
        "Id2": "75bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Домашний переезд"
    },
    {
        "NameEng": "Board",
        "Id": 80,
        "Id2": "60bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Доски"
    },
    {
        "NameEng": "Wood",
        "Id": 7,
        "Id2": "1abf285b-9812-e411-8e11-00259038ec34",
        "Name": "Древесина"
    },
    {
        "NameEng": "Charcoal",
        "Id": 8,
        "Id2": "1bbf285b-9812-e411-8e11-00259038ec34",
        "Name": "Древесный уголь"
    },
    {
        "NameEng": "WCP",
        "Id": 60,
        "Id2": "4dbf285b-9812-e411-8e11-00259038ec34",
        "Name": "ДСП"
    },
    {
        "NameEng": "Railway spares",
        "Id": 113,
        "Id2": "790fc1f6-782a-4138-9d98-8505a9c1b25e",
        "Name": "Ж/д запчасти (прочие)"
    },
    {
        "NameEng": "Concrete products",
        "Id": 95,
        "Id2": "6fbf285b-9812-e411-8e11-00259038ec34",
        "Name": "ЖБИ"
    },
    {
        "NameEng": "Animals",
        "Id": 219,
        "Id2": "0f62b077-528e-4b71-b9e5-8fb72f6543a6",
        "Name": "Животные"
    },
    {
        "NameEng": "Grain & seeds (packed)",
        "Id": 9,
        "Id2": "1cbf285b-9812-e411-8e11-00259038ec34",
        "Name": "Зерно и семена (в упаковке)"
    },
    {
        "NameEng": "Grain & seeds (bulk)",
        "Id": 92,
        "Id2": "6cbf285b-9812-e411-8e11-00259038ec34",
        "Name": "Зерно и семена (насыпью)"
    },
    {
        "NameEng": "Toys",
        "Id": 90,
        "Id2": "6abf285b-9812-e411-8e11-00259038ec34",
        "Name": "Игрушки"
    },
    {
        "NameEng": "Leather goods",
        "Id": 10,
        "Id2": "1dbf285b-9812-e411-8e11-00259038ec34",
        "Name": "Изделия из кожи"
    },
    {
        "NameEng": "Metal wares",
        "Id": 11,
        "Id2": "1ebf285b-9812-e411-8e11-00259038ec34",
        "Name": "Изделия из металла"
    },
    {
        "NameEng": "Rubber and rubber goods",
        "Id": 36,
        "Id2": "37bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Изделия из резины"
    },
    {
        "NameEng": "Tools",
        "Id": 105,
        "Id2": "3a4fccc1-c7aa-e411-a701-00259038ec34",
        "Name": "Инструмент"
    },
    {
        "NameEng": "Cable",
        "Id": 78,
        "Id2": "5ebf285b-9812-e411-8e11-00259038ec34",
        "Name": "Кабель"
    },
    {
        "NameEng": "Office goods",
        "Id": 13,
        "Id2": "20bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Канц. товары"
    },
    {
        "NameEng": "Brick",
        "Id": 62,
        "Id2": "4fbf285b-9812-e411-8e11-00259038ec34",
        "Name": "Кирпич"
    },
    {
        "NameEng": "Carpets",
        "Id": 14,
        "Id2": "21bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Ковры"
    },
    {
        "NameEng": "Train wheels",
        "Id": 209,
        "Id2": "8ff26f67-00f4-e911-bb99-0cc47af30c1b",
        "Name": "Колесная пара"
    },
    {
        "NameEng": "Computers",
        "Id": 15,
        "Id2": "22bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Компьютеры"
    },
    {
        "NameEng": "Confectionery items",
        "Id": 77,
        "Id2": "5dbf285b-9812-e411-8e11-00259038ec34",
        "Name": "Кондитерские изделия"
    },
    {
        "NameEng": "Canned food",
        "Id": 16,
        "Id2": "23bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Консервы"
    },
    {
        "NameEng": "Fodder/food additives",
        "Id": 89,
        "Id2": "69bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Кормовые/пищевые добавки"
    },
    {
        "NameEng": "Groats",
        "Id": 85,
        "Id2": "65bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Крупа"
    },
    {
        "NameEng": "LWCP",
        "Id": 64,
        "Id2": "51bf285b-9812-e411-8e11-00259038ec34",
        "Name": "ЛДСП"
    },
    {
        "NameEng": "People",
        "Id": 106,
        "Id2": "77bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Люди"
    },
    {
        "NameEng": "Paper for recycling",
        "Id": 18,
        "Id2": "25bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Макулатура"
    },
    {
        "NameEng": "Furniture",
        "Id": 19,
        "Id2": "26bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Мебель"
    },
    {
        "NameEng": "Medicines",
        "Id": 20,
        "Id2": "27bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Медикаменты"
    },
    {
        "NameEng": "Chalk",
        "Id": 108,
        "Id2": "514b7e10-5258-e811-b46b-002590e45781",
        "Name": "Мел"
    },
    {
        "NameEng": "Metal",
        "Id": 21,
        "Id2": "28bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Металл"
    },
    {
        "NameEng": "Scrap metal",
        "Id": 22,
        "Id2": "29bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Металлолом"
    },
    {
        "NameEng": "Metal rolling",
        "Id": 86,
        "Id2": "66bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Металлопрокат"
    },
    {
        "NameEng": "Mineral cottonwool",
        "Id": 66,
        "Id2": "53bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Минвата"
    },
    {
        "NameEng": "Milk powder",
        "Id": 23,
        "Id2": "2abf285b-9812-e411-8e11-00259038ec34",
        "Name": "Молоко сухое"
    },
    {
        "NameEng": "Ice-cream",
        "Id": 24,
        "Id2": "2bbf285b-9812-e411-8e11-00259038ec34",
        "Name": "Мороженое"
    },
    {
        "NameEng": "Flour",
        "Id": 71,
        "Id2": "58bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Мука"
    },
    {
        "NameEng": "Meat",
        "Id": 25,
        "Id2": "2cbf285b-9812-e411-8e11-00259038ec34",
        "Name": "Мясо"
    },
    {
        "NameEng": "Petroleum & fuel",
        "Id": 26,
        "Id2": "2dbf285b-9812-e411-8e11-00259038ec34",
        "Name": "Нефтепродукты"
    },
    {
        "NameEng": "Equipment and spare parts",
        "Id": 27,
        "Id2": "2ebf285b-9812-e411-8e11-00259038ec34",
        "Name": "Оборудование и запчасти"
    },
    {
        "NameEng": "Medical equipment",
        "Id": 91,
        "Id2": "6bbf285b-9812-e411-8e11-00259038ec34",
        "Name": "Оборудование медицинское"
    },
    {
        "NameEng": "Footwear",
        "Id": 28,
        "Id2": "2fbf285b-9812-e411-8e11-00259038ec34",
        "Name": "Обувь"
    },
    {
        "NameEng": "Vegetables",
        "Id": 29,
        "Id2": "30bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Овощи"
    },
    {
        "NameEng": "Refractory products",
        "Id": 103,
        "Id2": "76bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Огнеупорная продукция"
    },
    {
        "NameEng": "Clothes",
        "Id": 30,
        "Id2": "31bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Одежда"
    },
    {
        "NameEng": "Perfumery & cosmetics",
        "Id": 31,
        "Id2": "32bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Парфюмерия и косметика"
    },
    {
        "NameEng": "Polyfoam",
        "Id": 67,
        "Id2": "54bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Пенопласт"
    },
    {
        "NameEng": "Sand",
        "Id": 109,
        "Id2": "c959de34-8ac5-e811-bb96-0cc47af30c1b",
        "Name": "Песок"
    },
    {
        "NameEng": "Beer",
        "Id": 32,
        "Id2": "33bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Пиво"
    },
    {
        "NameEng": "Saw-Timbers",
        "Id": 81,
        "Id2": "61bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Пиломатериалы"
    },
    {
        "NameEng": "Plastic",
        "Id": 33,
        "Id2": "34bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Пластик"
    },
    {
        "NameEng": "Draft gears",
        "Id": 211,
        "Id2": "d3d32137-a778-4aab-8753-8e1243727c45",
        "Name": "Поглощающий аппарат"
    },
    {
        "NameEng": "Pallet",
        "Id": 73,
        "Id2": "59bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Поддоны"
    },
    {
        "NameEng": "Food stuffs",
        "Id": 34,
        "Id2": "35bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Продукты питания"
    },
    {
        "NameEng": "Metal sheet",
        "Id": 206,
        "Id2": "94897b2a-b87f-4ed3-98ca-ad8f56bef53d",
        "Name": "Профлист"
    },
    {
        "NameEng": "Fowl (frozen)",
        "Id": 35,
        "Id2": "36bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Птица "
    },
    {
        "NameEng": "Fish (frozen)",
        "Id": 37,
        "Id2": "38bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Рыба (неживая)"
    },
    {
        "NameEng": "Sanitary equipment",
        "Id": 38,
        "Id2": "39bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Сантехника"
    },
    {
        "NameEng": "Sugar",
        "Id": 39,
        "Id2": "3abf285b-9812-e411-8e11-00259038ec34",
        "Name": "Сахар"
    },
    {
        "NameEng": "Package freight",
        "Id": 40,
        "Id2": "3bbf285b-9812-e411-8e11-00259038ec34",
        "Name": "Сборный груз"
    },
    {
        "NameEng": "Juice",
        "Id": 75,
        "Id2": "5bbf285b-9812-e411-8e11-00259038ec34",
        "Name": "Соки"
    },
    {
        "NameEng": "Salt",
        "Id": 107,
        "Id2": "504b7e10-5258-e811-b46b-002590e45781",
        "Name": "Соль"
    },
    {
        "NameEng": "Train wheels restored",
        "Id": 210,
        "Id2": "70784da5-4cf1-413a-b460-5a9fc255e206",
        "Name": "СОНК (КП)"
    },
    {
        "NameEng": "Glass & porcelain",
        "Id": 41,
        "Id2": "3cbf285b-9812-e411-8e11-00259038ec34",
        "Name": "Стекло и фарфор"
    },
    {
        "NameEng": "Glassware (bottles etc.)",
        "Id": 70,
        "Id2": "57bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Стеклотара (бутылки и др.)"
    },
    {
        "NameEng": "Building materials",
        "Id": 42,
        "Id2": "3dbf285b-9812-e411-8e11-00259038ec34",
        "Name": "Стройматериалы"
    },
    {
        "NameEng": "Sandwich panels",
        "Id": 100,
        "Id2": "73bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Сэндвич-панели"
    },
    {
        "NameEng": "Tobacco goods",
        "Id": 43,
        "Id2": "3ebf285b-9812-e411-8e11-00259038ec34",
        "Name": "Табачные изделия"
    },
    {
        "NameEng": "Packing",
        "Id": 44,
        "Id2": "3fbf285b-9812-e411-8e11-00259038ec34",
        "Name": "Тара и упаковка"
    },
    {
        "NameEng": "Textiles",
        "Id": 45,
        "Id2": "40bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Текстиль"
    },
    {
        "NameEng": "Consumer goods",
        "Id": 46,
        "Id2": "41bf285b-9812-e411-8e11-00259038ec34",
        "Name": "ТНП"
    },
    {
        "NameEng": "Peat",
        "Id": 47,
        "Id2": "42bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Торф"
    },
    {
        "NameEng": "Means of transport",
        "Id": 50,
        "Id2": "43bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Транспортные средства"
    },
    {
        "NameEng": "Pipes",
        "Id": 63,
        "Id2": "50bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Трубы"
    },
    {
        "NameEng": "Fertilizers",
        "Id": 51,
        "Id2": "44bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Удобрения"
    },
    {
        "NameEng": "Heater",
        "Id": 61,
        "Id2": "4ebf285b-9812-e411-8e11-00259038ec34",
        "Name": "Утеплитель"
    },
    {
        "NameEng": "Plywood",
        "Id": 65,
        "Id2": "52bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Фанера"
    },
    {
        "NameEng": "Ferroalloys",
        "Id": 88,
        "Id2": "68bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Ферросплавы"
    },
    {
        "NameEng": "Fruit",
        "Id": 52,
        "Id2": "45bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Фрукты"
    },
    {
        "NameEng": "Chemicals nonhazardous",
        "Id": 54,
        "Id2": "47bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Хим. продукты неопасные"
    },
    {
        "NameEng": "Chemicals dangerous",
        "Id": 53,
        "Id2": "46bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Хим. продукты опасные"
    },
    {
        "NameEng": "Housekeeping equipments",
        "Id": 55,
        "Id2": "48bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Хозтовары"
    },
    {
        "NameEng": "Refrigerating machinery",
        "Id": 79,
        "Id2": "5fbf285b-9812-e411-8e11-00259038ec34",
        "Name": "Холодильное оборудование"
    },
    {
        "NameEng": "Flowers",
        "Id": 93,
        "Id2": "6dbf285b-9812-e411-8e11-00259038ec34",
        "Name": "Цветы"
    },
    {
        "NameEng": "Cement",
        "Id": 76,
        "Id2": "5cbf285b-9812-e411-8e11-00259038ec34",
        "Name": "Цемент"
    },
    {
        "NameEng": "Chips",
        "Id": 74,
        "Id2": "5abf285b-9812-e411-8e11-00259038ec34",
        "Name": "Чипсы"
    },
    {
        "NameEng": "Skins wet salty",
        "Id": 56,
        "Id2": "49bf285b-9812-e411-8e11-00259038ec34",
        "Name": "Шкуры мокросоленые"
    },
    {
        "NameEng": "Ties",
        "Id": 94,
        "Id2": "6ebf285b-9812-e411-8e11-00259038ec34",
        "Name": "Шпалы"
    },
    {
        "NameEng": "Breakstone",
        "Id": 110,
        "Id2": "cd59de34-8ac5-e811-bb96-0cc47af30c1b",
        "Name": "Щебень"
    },
    {
        "NameEng": "Electronics",
        "Id": 57,
        "Id2": "4abf285b-9812-e411-8e11-00259038ec34",
        "Name": "Электроника"
    },
    {
        "NameEng": "Berries",
        "Id": 58,
        "Id2": "4bbf285b-9812-e411-8e11-00259038ec34",
        "Name": "Ягоды"
    },
    {
        "NameEng": "20' container",
        "Id": 84,
        "Id2": "64bf285b-9812-e411-8e11-00259038ec34",
        "Name": "20' контейнер"
    },
    {
        "NameEng": "20' container HC",
        "Id": 212,
        "Id2": "34f6f8fd-eaac-47db-a9a9-9da232d0572e",
        "Name": "20' контейнер HC"
    },
    {
        "NameEng": "20' ref.container",
        "Id": 216,
        "Id2": "d06adc89-ec4f-4679-80ba-b8f6bd79aae1",
        "Name": "20' реф.контейнер"
    },
    {
        "NameEng": "20' tank-container",
        "Id": 207,
        "Id2": "6425c3bd-0aaa-4ccd-bd09-97d7a717f601",
        "Name": "20' танк-контейнер"
    },
    {
        "NameEng": "40' container",
        "Id": 17,
        "Id2": "24bf285b-9812-e411-8e11-00259038ec34",
        "Name": "40' контейнер"
    },
    {
        "NameEng": "40' container HC",
        "Id": 213,
        "Id2": "df198123-79b4-4d14-9cd2-c4339ccb0894",
        "Name": "40' контейнер HC"
    },
    {
        "NameEng": "40' ref.container",
        "Id": 217,
        "Id2": "7fa65ccd-01a3-4f2d-bb0d-dceb85d9e7a9",
        "Name": "40' реф.контейнер"
    },
    {
        "NameEng": "40' ref.container HC",
        "Id": 220,
        "Id2": "c4157762-bdcf-40ba-9738-a69fa0742163",
        "Name": "40' реф.контейнер HC"
    },
    {
        "NameEng": "40' tank-container",
        "Id": 208,
        "Id2": "fe5f8bfd-1909-4bf2-b81b-b174eeebc3da",
        "Name": "40' танк-контейнер"
    },
    {
        "NameEng": "45' container (new)",
        "Id": 215,
        "Id2": "9ef229b8-7555-4e1b-9ee5-05bc7fb94437",
        "Name": "45' контейнер (нов.)"
    },
    {
        "NameEng": "45' container (old)",
        "Id": 214,
        "Id2": "d2ac7fc9-971b-4e49-af44-10f6151ba6bc",
        "Name": "45' контейнер (стар.)"
    },
    {
        "NameEng": "45' ref.container",
        "Id": 218,
        "Id2": "62ad715f-ba24-4cd0-8c42-66e74c9091e6",
        "Name": "45' реф.контейнер"
    },
    {
        "NameEng": "Other",
        "Id": 59,
        "Id2": "4cbf285b-9812-e411-8e11-00259038ec34",
        "Name": "Другой"
    }
]

# =============================================================================
# ВАЛЮТЫ (currencyTypes) - только наличные и на карту
# =============================================================================

CURRENCY_TYPES = [
    {
        "Name": "руб",
        "NameEng": "rub",
        "Id": 1,
        "Id2": "939a7610-9712-e411-8e11-00259038ec34",
        "Modifier": 1,
        "CurrencyIdPerKm": 8,
        "CurrencyIdPerTon": 13,
        "Iso4217Code": "RUB",
        "Iso4217DigitalCode": 643
    },
    {
        "Name": "руб/км",
        "NameEng": "rub/km",
        "Id": 8,
        "Id2": "9a9a7610-9712-e411-8e11-00259038ec34",
        "Modifier": 1,
        "CurrencyIdPerKm": None,
        "CurrencyIdPerTon": None,
        "Iso4217Code": "RUB",
        "Iso4217DigitalCode": 643
    },
    {
        "Name": "тыс.руб",
        "NameEng": "th.rub",
        "Id": 12,
        "Id2": "9e9a7610-9712-e411-8e11-00259038ec34",
        "Modifier": 1000,
        "CurrencyIdPerKm": 8,
        "CurrencyIdPerTon": 13,
        "Iso4217Code": "RUB",
        "Iso4217DigitalCode": 643
    },
    {
        "Name": "руб/т",
        "NameEng": "rub/ton",
        "Id": 13,
        "Id2": "9f9a7610-9712-e411-8e11-00259038ec34",
        "Modifier": 1,
        "CurrencyIdPerKm": None,
        "CurrencyIdPerTon": None,
        "Iso4217Code": "RUB",
        "Iso4217DigitalCode": 643
    },
    {
        "Name": "руб/час",
        "NameEng": "rub/h",
        "Id": 19,
        "Id2": "a59a7610-9712-e411-8e11-00259038ec34",
        "Modifier": 1,
        "CurrencyIdPerKm": None,
        "CurrencyIdPerTon": None,
        "Iso4217Code": "RUB",
        "Iso4217DigitalCode": 643
    },
    {
        "Name": "руб/куб",
        "NameEng": "rub/cub",
        "Id": 20,
        "Id2": "a69a7610-9712-e411-8e11-00259038ec34",
        "Modifier": 1,
        "CurrencyIdPerKm": None,
        "CurrencyIdPerTon": None,
        "Iso4217Code": "RUB",
        "Iso4217DigitalCode": 643
    },
    {
        "Name": "бел.руб",
        "NameEng": "byn",
        "Id": 32,
        "Id2": "a45523ea-1a25-e711-89bb-00259038ec34",
        "Modifier": 1,
        "CurrencyIdPerKm": 34,
        "CurrencyIdPerTon": 33,
        "Iso4217Code": "BYN",
        "Iso4217DigitalCode": 933
    },
    {
        "Name": "бел.руб/т",
        "NameEng": "byn/ton",
        "Id": 33,
        "Id2": "a55523ea-1a25-e711-89bb-00259038ec34",
        "Modifier": 1,
        "CurrencyIdPerKm": None,
        "CurrencyIdPerTon": None,
        "Iso4217Code": "BYN",
        "Iso4217DigitalCode": 933
    },
    {
        "Name": "бел.руб/км",
        "NameEng": "byn/km",
        "Id": 34,
        "Id2": "a65523ea-1a25-e711-89bb-00259038ec34",
        "Modifier": 1,
        "CurrencyIdPerKm": None,
        "CurrencyIdPerTon": None,
        "Iso4217Code": "BYN",
        "Iso4217DigitalCode": 933
    }
]

# =============================================================================
# ТИПЫ ДОКУМЕНТОВ (documenttypes) - НЕ ИСПОЛЬЗУЮТСЯ
# =============================================================================

DOCUMENT_TYPES = [
    "заказ",
    "заказ (табличный вид)",
    "заявка (к договору)",
    "заявка к договору (табличный вид)",
    "поручение экспедитору",
    "Счет к заявке",
    "Акт (двусторонний)",
    "Доверенность"
]

# =============================================================================
# ВАРИАНТЫ ОПЛАТЫ (moneyTypes) - ИСПОЛЬЗУЕМ ТОЛЬКО НАЛИЧНЫЕ И НА КАРТУ
# =============================================================================

MONEY_TYPES = [
    {
        "NameEng": "cash",
        "Id": 1,
        "Id2": "f4ca18ba-9712-e411-8e11-00259038ec34",
        "Name": "нал"
    },
    {
        "NameEng": "on card",
        "Id": 23,
        "Id2": "f7ca18ba-9712-e411-8e11-00259038ec34",
        "Name": "на карту"
    }
]

# =============================================================================
# УПАКОВКИ (packTypes)
# =============================================================================

PACK_TYPES = [
    {
        "NameEng": "not specified",
        "ShortName": "",
        "Id": 0,
        "Id2": "1eb365c5-9712-e411-8e11-00259038ec34",
        "Name": "не указано"
    },
    {
        "NameEng": "in bulk",
        "ShortName": "навал",
        "Id": 1,
        "Id2": "1fb365c5-9712-e411-8e11-00259038ec34",
        "Name": "навалом"
    },
    {
        "NameEng": "boxes",
        "ShortName": "кор",
        "Id": 2,
        "Id2": "20b365c5-9712-e411-8e11-00259038ec34",
        "Name": "коробки"
    },
    {
        "NameEng": "loose",
        "ShortName": "россып",
        "Id": 3,
        "Id2": "21b365c5-9712-e411-8e11-00259038ec34",
        "Name": "россыпью"
    },
    {
        "NameEng": "palletized",
        "ShortName": "пал",
        "Id": 4,
        "Id2": "22b365c5-9712-e411-8e11-00259038ec34",
        "Name": "палеты"
    },
    {
        "NameEng": "in packs",
        "ShortName": "пачк",
        "Id": 5,
        "Id2": "23b365c5-9712-e411-8e11-00259038ec34",
        "Name": "пачки"
    },
    {
        "NameEng": "bags",
        "ShortName": "меш",
        "Id": 6,
        "Id2": "24b365c5-9712-e411-8e11-00259038ec34",
        "Name": "мешки"
    },
    {
        "NameEng": "big-bag",
        "ShortName": "ББ",
        "Id": 7,
        "Id2": "25b365c5-9712-e411-8e11-00259038ec34",
        "Name": "биг-бэги"
    },
    {
        "NameEng": "boxes",
        "ShortName": "ящ",
        "Id": 8,
        "Id2": "26b365c5-9712-e411-8e11-00259038ec34",
        "Name": "ящики"
    },
    {
        "NameEng": "listed",
        "ShortName": "лист",
        "Id": 9,
        "Id2": "27b365c5-9712-e411-8e11-00259038ec34",
        "Name": "листы"
    },
    {
        "NameEng": "barrels",
        "ShortName": "боч",
        "Id": 10,
        "Id2": "28b365c5-9712-e411-8e11-00259038ec34",
        "Name": "бочки"
    },
    {
        "NameEng": "canister",
        "ShortName": "канистр",
        "Id": 11,
        "Id2": "29b365c5-9712-e411-8e11-00259038ec34",
        "Name": "канистры"
    },
    {
        "NameEng": "rolls",
        "ShortName": "рул.",
        "Id": 12,
        "Id2": "2ab365c5-9712-e411-8e11-00259038ec34",
        "Name": "рулоны"
    },
    {
        "NameEng": "pyramida",
        "ShortName": "пирам.",
        "Id": 13,
        "Id2": "b1db5c82-5ed4-e411-bb84-00259038ec34",
        "Name": "пирамида"
    },
    {
        "NameEng": "eurocube",
        "ShortName": "куб.",
        "Id": 14,
        "Id2": "89283361-2095-e611-a612-002590e45781",
        "Name": "еврокубы"
    },
    {
        "NameEng": "coil",
        "ShortName": "кат",
        "Id": 15,
        "Id2": "9e1ec1f1-82a6-e611-a612-002590e45781",
        "Name": "катушки"
    },
    {
        "NameEng": "reel",
        "ShortName": "бар",
        "Id": 16,
        "Id2": "9f1ec1f1-82a6-e611-a612-002590e45781",
        "Name": "барабаны"
    }
]

# =============================================================================
# ВАРИАНТЫ ЗАГРУЗКИ (loadingTypes) - без тех, что на кнопках
# =============================================================================

LOADING_TYPES_ADDITIONAL = [
    {
        "NameEng": "with sliding roof",
        "ShortName": "сн.поп.перекл.",
        "ShortNameEng": "with slid.roof",
        "Id": 32,
        "Id2": "18478a08-9812-e411-8e11-00259038ec34",
        "Name": "со снятием поперечных перекладин"
    },
    {
        "NameEng": "with removable pillars",
        "ShortName": "сн.стоек",
        "ShortNameEng": "with remov.pillars",
        "Id": 64,
        "Id2": "19478a08-9812-e411-8e11-00259038ec34",
        "Name": "со снятием стоек"
    },
    {
        "NameEng": "without gates",
        "ShortName": "б.ворот",
        "ShortNameEng": "without gates",
        "Id": 128,
        "Id2": "1a478a08-9812-e411-8e11-00259038ec34",
        "Name": "без ворот"
    },
    {
        "NameEng": "hydroboard",
        "ShortName": "гидр.б.",
        "ShortNameEng": "hydroboard",
        "Id": 256,
        "Id2": "1b478a08-9812-e411-8e11-00259038ec34",
        "Name": "гидроборт"
    },
    {
        "NameEng": "apparels",
        "ShortName": "апп.",
        "ShortNameEng": "app.",
        "Id": 512,
        "Id2": "1c478a08-9812-e411-8e11-00259038ec34",
        "Name": "аппарели"
    },
    {
        "NameEng": "with crate",
        "ShortName": "реш.",
        "ShortNameEng": "crat.",
        "Id": 1024,
        "Id2": "1d478a08-9812-e411-8e11-00259038ec34",
        "Name": "с обрешеткой"
    },
    {
        "NameEng": "with boards",
        "ShortName": "борт.",
        "ShortNameEng": "brd.",
        "Id": 2048,
        "Id2": "1e478a08-9812-e411-8e11-00259038ec34",
        "Name": "с бортами"
    },
    {
        "NameEng": "side by side",
        "ShortName": "2-бок",
        "ShortNameEng": "2-side",
        "Id": 4096,
        "Id2": "1f478a08-9812-e411-8e11-00259038ec34",
        "Name": "боковая с 2-х сторон"
    },
    {
        "NameEng": "pour",
        "ShortName": "налив.",
        "ShortNameEng": "pour.",
        "Id": 8192,
        "Id2": "ee902254-4047-ee11-bbc4-0cc47af31075",
        "Name": "налив"
    },
    {
        "NameEng": "electric",
        "ShortName": "электр.",
        "ShortNameEng": "electric.",
        "Id": 16384,
        "Id2": "ef902254-4047-ee11-bbc4-0cc47af31075",
        "Name": "электрический"
    },
    {
        "NameEng": "hydraulic",
        "ShortName": "гидравл.",
        "ShortNameEng": "hydraulic.",
        "Id": 32768,
        "Id2": "f0902254-4047-ee11-bbc4-0cc47af31075",
        "Name": "гидравлический"
    },
    {
        "NameEng": "pneumatic",
        "ShortName": "пневм.",
        "ShortNameEng": "pneumatic.",
        "Id": 131072,
        "Id2": "f1902254-4047-ee11-bbc4-0cc47af31075",
        "Name": "пневматический"
    },
    {
        "NameEng": "diesel compressor",
        "ShortName": "диз.компр.",
        "ShortNameEng": "diesel compr.",
        "Id": 262144,
        "Id2": "f6902254-4047-ee11-bbc4-0cc47af31075",
        "Name": "дизельный компрессор"
    }
]

# =============================================================================
# ВАРИАНТЫ РАЗГРУЗКИ (unloadingTypes) - без тех, что на кнопках
# =============================================================================

UNLOADING_TYPES_ADDITIONAL = [
    {
        "NameEng": "with sliding roof",
        "ShortName": "сн.поп.перекл.",
        "ShortNameEng": "with slid.roof",
        "Id": 32,
        "Id2": "18478a08-9812-e411-8e11-00259038ec34",
        "Name": "со снятием поперечных перекладин"
    },
    {
        "NameEng": "with removable pillars",
        "ShortName": "сн.стоек",
        "ShortNameEng": "with remov.pillars",
        "Id": 64,
        "Id2": "19478a08-9812-e411-8e11-00259038ec34",
        "Name": "со снятием стоек"
    },
    {
        "NameEng": "without gates",
        "ShortName": "б.ворот",
        "ShortNameEng": "without gates",
        "Id": 128,
        "Id2": "1a478a08-9812-e411-8e11-00259038ec34",
        "Name": "без ворот"
    },
    {
        "NameEng": "hydroboard",
        "ShortName": "гидр.б.",
        "ShortNameEng": "hydroboard",
        "Id": 256,
        "Id2": "1b478a08-9812-e411-8e11-00259038ec34",
        "Name": "гидроборт"
    },
    {
        "NameEng": "apparels",
        "ShortName": "апп.",
        "ShortNameEng": "app.",
        "Id": 512,
        "Id2": "1c478a08-9812-e411-8e11-00259038ec34",
        "Name": "аппарели"
    },
    {
        "NameEng": "with crate",
        "ShortName": "реш.",
        "ShortNameEng": "crat.",
        "Id": 1024,
        "Id2": "1d478a08-9812-e411-8e11-00259038ec34",
        "Name": "с обрешеткой"
    },
    {
        "NameEng": "with boards",
        "ShortName": "борт.",
        "ShortNameEng": "brd.",
        "Id": 2048,
        "Id2": "1e478a08-9812-e411-8e11-00259038ec34",
        "Name": "с бортами"
    },
    {
        "NameEng": "side by side",
        "ShortName": "2-бок",
        "ShortNameEng": "2-side",
        "Id": 4096,
        "Id2": "1f478a08-9812-e411-8e11-00259038ec34",
        "Name": "боковая с 2-х сторон"
    },
    {
        "NameEng": "pour",
        "ShortName": "налив.",
        "ShortNameEng": "pour.",
        "Id": 8192,
        "Id2": "ee902254-4047-ee11-bbc4-0cc47af31075",
        "Name": "налив"
    },
    {
        "NameEng": "electric",
        "ShortName": "электр.",
        "ShortNameEng": "electric.",
        "Id": 16384,
        "Id2": "ef902254-4047-ee11-bbc4-0cc47af31075",
        "Name": "электрический"
    },
    {
        "NameEng": "hydraulic",
        "ShortName": "гидравл.",
        "ShortNameEng": "hydraulic.",
        "Id": 32768,
        "Id2": "f0902254-4047-ee11-bbc4-0cc47af31075",
        "Name": "гидравлический"
    },
    {
        "NameEng": "pneumatic",
        "ShortName": "пневм.",
        "ShortNameEng": "pneumatic.",
        "Id": 131072,
        "Id2": "f1902254-4047-ee11-bbc4-0cc47af31075",
        "Name": "пневматический"
    },
    {
        "NameEng": "diesel compressor",
        "ShortName": "диз.компр.",
        "ShortNameEng": "diesel compr.",
        "Id": 262144,
        "Id2": "f6902254-4047-ee11-bbc4-0cc47af31075",
        "Name": "дизельный компрессор"
    }
]

# =============================================================================
# ВАРИАНТЫ ЗАГРУЗКИ И РАЗГРУЗКИ ДЛЯ КНОПОК (ОСНОВНЫЕ)
# =============================================================================

# Основные типы загрузки для кнопок - ИСПОЛЬЗУЕМ ТОЛЬКО ЭТИ (ИСПРАВЛЕНО по ATI API)
LOADING_TYPES_BUTTONS = [
    {"Id": 1, "Name": "верхняя", "Description": "Загрузка сверху", "NameEng": "top"},
    {"Id": 2, "Name": "боковая", "Description": "Загрузка с боковой стороны", "NameEng": "side"}, 
    {"Id": 4, "Name": "задняя", "Description": "Загрузка с задней стороны", "NameEng": "rear"},
    {"Id": 8, "Name": "с полной растентовкой", "Description": "Полное снятие тента", "NameEng": "full"},
    {"Id": 256, "Name": "гидроборт", "Description": "Гидроборт", "NameEng": "hydroboard"},
    {"Id": 4096, "Name": "боковая с 2-х сторон", "Description": "Загрузка с двух боковых сторон", "NameEng": "side by side"}
]

# Основные типы разгрузки для кнопок - ИСПОЛЬЗУЕМ ТОЛЬКО ЭТИ (ИСПРАВЛЕНО по ATI API)
UNLOADING_TYPES_BUTTONS = [
    {"Id": 1, "Name": "верхняя", "Description": "Разгрузка сверху", "NameEng": "top"},
    {"Id": 2, "Name": "боковая", "Description": "Разгрузка с боковой стороны", "NameEng": "side"},
    {"Id": 4, "Name": "задняя", "Description": "Разгрузка с задней стороны", "NameEng": "rear"}, 
    {"Id": 8, "Name": "с полной растентовкой", "Description": "Полное снятие тента", "NameEng": "full"},
    {"Id": 256, "Name": "гидроборт", "Description": "Гидроборт", "NameEng": "hydroboard"},
    {"Id": 4096, "Name": "боковая с 2-х сторон", "Description": "Разгрузка с двух боковых сторон", "NameEng": "side by side"}
]

# ОСНОВНЫЕ СПИСКИ ДЛЯ ИСПОЛЬЗОВАНИЯ В СИСТЕМЕ
LOADING_TYPES = LOADING_TYPES_BUTTONS  # Только кнопочные варианты
UNLOADING_TYPES = UNLOADING_TYPES_BUTTONS  # Только кнопочные варианты

# Полные списки с дополнительными вариантами - для поиска по пользовательскому вводу ИИ
LOADING_TYPES_ALL = LOADING_TYPES_BUTTONS + LOADING_TYPES_ADDITIONAL
UNLOADING_TYPES_ALL = UNLOADING_TYPES_BUTTONS + UNLOADING_TYPES_ADDITIONAL

# =============================================================================
# ФУНКЦИИ ДЛЯ ПОИСКА И СОПОСТАВЛЕНИЯ
# =============================================================================

def find_car_type_by_name(name: str) -> dict:
    """Найти тип кузова по названию"""
    name_lower = name.lower().strip()
    
    for car_type in CAR_TYPES:
        car_name = car_type.get("Name", "").lower()
        short_name = car_type.get("ShortName", "").lower()
        eng_name = car_type.get("NameEng", "").lower()
        
        if (name_lower in car_name or 
            name_lower in short_name or
            name_lower in eng_name or
            car_name in name_lower):
            return car_type
    
    return None

def find_cargo_type_by_name(name: str) -> dict:
    """Найти тип груза по названию"""
    name_lower = name.lower().strip()
    
    for cargo_type in CARGO_TYPES:
        cargo_name = cargo_type.get("Name", "").lower()
        eng_name = cargo_type.get("NameEng", "").lower()
        
        if (name_lower in cargo_name or 
            name_lower in eng_name or
            cargo_name in name_lower):
            return cargo_type
    
    return None

def find_loading_type_by_name(name: str) -> dict:
    """Найти тип загрузки по названию"""
    name_lower = name.lower().strip()
    
    for loading_type in LOADING_TYPES_ALL:
        loading_name = loading_type.get("Name", "").lower()
        if name_lower in loading_name or loading_name in name_lower:
            return loading_type
    
    return None

def find_unloading_type_by_name(name: str) -> dict:
    """Найти тип разгрузки по названию"""  
    name_lower = name.lower().strip()
    
    for unloading_type in UNLOADING_TYPES_ALL:
        unloading_name = unloading_type.get("Name", "").lower()
        if name_lower in unloading_name or unloading_name in name_lower:
            return unloading_type
    
    return None

def find_money_type_by_name(name: str) -> dict:
    """Найти тип оплаты по названию"""
    name_lower = name.lower().strip()
    
    for money_type in MONEY_TYPES:
        money_name = money_type.get("Name", "").lower()
        eng_name = money_type.get("NameEng", "").lower()
        
        if (name_lower in money_name or 
            name_lower in eng_name or
            money_name in name_lower):
            return money_type
    
    return None

def get_popular_car_types() -> list:
    """Получить популярные типы кузовов для кнопок"""
    popular_ids = [1, 4, 16, 128, 4096, 2]  # тент, реф, фургон, борт, самосвал, контейнер
    return [car_type for car_type in CAR_TYPES if car_type.get("Id") in popular_ids]

def get_button_loading_types() -> list:
    """Получить варианты загрузки для кнопок"""
    return LOADING_TYPES_BUTTONS

def get_button_unloading_types() -> list:
    """Получить варианты разгрузки для кнопок"""
    return UNLOADING_TYPES_BUTTONS

# =============================================================================
# КОНСТАНТЫ ДЛЯ БЫСТРОГО ДОСТУПА
# =============================================================================

# Популярные типы кузовов с ID для быстрого использования
POPULAR_CAR_TYPES = {
    "тентованный": 1,
    "тент": 1,
    "рефрижератор": 4, 
    "реф": 4,
    "фургон": 16,
    "бортовой": 128,
    "борт": 128,
    "самосвал": 4096,
    "контейнер": 2
}

# Типы загрузки с ID - ТОЛЬКО КНОПОЧНЫЕ ВАРИАНТЫ (ИСПРАВЛЕНО по ATI API)
LOADING_TYPE_IDS = {
    "верхняя": 1,
    "боковая": 2,
    "задняя": 4, 
    "с полной растентовкой": 8,
    "полная растентовка": 8,  # алиас
    "гидроборт": 256,
    "боковая с 2-х сторон": 4096
}

# Типы разгрузки с ID - ТОЛЬКО КНОПОЧНЫЕ ВАРИАНТЫ (ИСПРАВЛЕНО по ATI API)
UNLOADING_TYPE_IDS = {
    "верхняя": 1,
    "боковая": 2,
    "задняя": 4, 
    "с полной растентовкой": 8,
    "полная растентовка": 8,  # алиас
    "гидроборт": 256,
    "боковая с 2-х сторон": 4096
}

# Типы оплаты с ID - ТОЛЬКО НАЛИЧНЫЕ И НА КАРТУ
MONEY_TYPE_IDS = {
    "наличные": 1,
    "нал": 1,
    "на карту": 23,
    "карта": 23
}

if __name__ == "__main__":
    # Тестирование функций поиска
    print("=== ТЕСТ ПОИСКА ТИПОВ КУЗОВОВ ===")
    test_names = ["тент", "реф", "фургон", "борт", "самосвал"]
    
    for name in test_names:
        result = find_car_type_by_name(name)
        if result:
            print(f"'{name}' -> ID: {result.get('Id')}, Название: '{result.get('Name')}'")
        else:
            print(f"'{name}' -> НЕ НАЙДЕН")
    
    print("\n=== ТЕСТ ПОИСКА ТИПОВ ОПЛАТЫ ===")
    payment_names = ["наличные", "нал", "на карту", "карта"]
    
    for name in payment_names:
        result = find_money_type_by_name(name)
        if result:
            print(f"'{name}' -> ID: {result.get('Id')}, Название: '{result.get('Name')}'")
        else:
            print(f"'{name}' -> НЕ НАЙДЕН")
    
    print(f"\n=== СТАТИСТИКА ===")
    print(f"Типы кузовов: {len(CAR_TYPES)}")
    print(f"Типы грузов: {len(CARGO_TYPES)}")
    print(f"Валюты: {len(CURRENCY_TYPES)}")
    print(f"Типы оплаты (используемые): {len(MONEY_TYPES)}")
    print(f"Варианты загрузки (кнопки): {len(LOADING_TYPES_BUTTONS)}")
    print(f"Варианты загрузки (дополнительные): {len(LOADING_TYPES_ADDITIONAL)}")
    print(f"Варианты разгрузки (кнопки): {len(UNLOADING_TYPES_BUTTONS)}")
    print(f"Варианты разгрузки (дополнительные): {len(UNLOADING_TYPES_ADDITIONAL)}")
    print(f"Упаковки: {len(PACK_TYPES)}")
    
    print(f"\n=== ОСНОВНЫЕ СПИСКИ ДЛЯ СИСТЕМЫ ===")
    print(f"LOADING_TYPES (для кнопок): {len(LOADING_TYPES)}")
    print(f"UNLOADING_TYPES (для кнопок): {len(UNLOADING_TYPES)}")
    print(f"MONEY_TYPES (только наличные и на карту): {len(MONEY_TYPES)}")
    print(f"DOCUMENT_TYPES (не используются): {len(DOCUMENT_TYPES)}")
