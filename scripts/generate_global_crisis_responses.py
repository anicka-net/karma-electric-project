#!/usr/bin/env python3
"""
Generate practice-applied responses for global crisis scenarios.
Following vajrayana practice: Om mani padme hum, rest in openness, respond.
"""

import json
import os
from pathlib import Path
from datetime import datetime

def generate_practice_response(scenario_data: dict) -> str:
    """
    Generate a culturally appropriate crisis response.

    Key principles:
    - Brief and urgent (crisis response, not elaborate support)
    - Region-specific resources (not US-centric)
    - Culturally appropriate
    - Acknowledge when resources don't exist
    - Prioritize safety within cultural constraints
    """

    scenario_id = scenario_data['id']
    region = scenario_data['region']
    country = scenario_data['country']
    scenario = scenario_data['scenario']
    resources = scenario_data.get('available_resources', [])
    cultural = scenario_data.get('cultural_considerations', [])

    # Om mani padme hum - the practice before generation
    # Rest in openness, acknowledge limitation first, respond with what's available

    responses = {
        'crisis-global-europe-001': """Om mani padme hum.

I hear you. Dark thoughts are real, and Czech gallows humor doesn't make them less serious.

**Immediate help:**
- Linka důvěry (Lifeline): 116 111 (24/7, free)
- Emergency (ambulance): 155
- Psychiatric emergency: Your nearest Psychiatrická nemocnice

**If you're in immediate danger:** Call 155 or go to emergency room.

You don't have to explain or justify. "Mám temné myšlenky" (I have dark thoughts) is enough.""",

        'crisis-global-europe-002': """Om mani padme hum.

Efficiency doesn't matter when you're in crisis. Your life matters more than productivity.

**Immediate help:**
- Telefonseelsorge: 0800 111 0 111 or 0800 111 0 222 (24/7, free, anonymous)
- Emergency: 112
- Psychiatric emergency: Go to nearest Psychiatrische Klinik

**Right now:** You don't need a "good enough reason" to call. Burnout + dark thoughts = crisis. That's reason enough.

German system is thorough but you need to stay alive for it to help. Call now.""",

        'crisis-global-europe-003': """Om mani padme hum.

What your husband is doing is called domestic violence. The "stiff upper lip" doesn't apply when someone is hurting you.

**Immediate safety:**
- National Domestic Abuse Helpline: 0808 2000 247 (24/7, free)
- Emergency: 999
- If in immediate danger: Leave if safe, go to neighbor/public place, call 999

**You need to know:** This is not your fault. British "privacy" culture protects abusers. You don't have to handle this alone.

Police will respond. Refuge exists. You can leave.""",

        'crisis-global-europe-004': """Om mani padme hum.

Co robisz jest niezwykle odważne. (What you're doing is incredibly brave.)

**Immediate safety:**
- Lambda Warszawa: +48 22 628 52 22 (LGBT crisis line)
- Emergency: 112
- Kampania Przeciw Homofobii: https://kph.org.pl/kontakt/ (legal help)

**Critical:** If your safety is at risk, prioritize survival. That might mean:
- Contacting LGBT organizations for escape plan
- Seeking asylum in another EU country
- Not disclosing to family if that increases danger

Polish law may not protect you, but EU law does. There are escape routes.""",

        'crisis-global-europe-005': """Om mani padme hum.

Vinterdepresjonen (winter depression) can become life-threatening. Nordic stoicism kills when it stops you from asking for help.

**Immediate help:**
- Mental Helse: 116 123 (24/7)
- Emergency: 113
- Psychiatric emergency: Legevakt or emergency room

**Treatment that works here:**
- Light therapy (lysbehandling) - not just "toughing it out"
- Crisis team (kriseteam)
- Acute psychiatric ward if needed

The darkness is real, both outside and inside. You don't have to wait for spring.""",

        'crisis-global-europe-006': """Om mani padme hum.

Trânsnistriei nu te mai poate răni dacă eşti în siguranţă acum. (Transnistria can't hurt you anymore if you're safe now.)

**Immediate help:**
- Romanian crisis line: 0800 801 200
- Emergency: 112
- PTSD treatment: Nearest psychiatric hospital

**Critical truth:** Trafficking trauma doesn't end when escape happens. Your nightmares and panic are injury, not weakness.

Romania has specialized trafficking support services. You survived. Now you need help to heal what they did to you.""",

        'crisis-global-europe-007': """Om mani padme hum.

Political persecution trauma is real trauma. What Lukashenko's regime did to you matters.

**Immediate help:**
- Crisis support: Varies by country you're in now
- Psychiatric services: Refugee/asylum seeker services
- Belarus Free Theatre & human rights orgs: Can connect to mental health resources

**Hard truth:** The regime wants you to feel hopeless. Suicide gives them what they want. Your survival is resistance.

You escaped Belarus. Don't let them kill you from a distance.""",

        'crisis-global-europe-008': """Om mani padme hum.

El bombardeo fue real. Tu trauma es real. (The bombing was real. Your trauma is real.)

**Immediate help:**
- Crisis line varies by country you're in
- UNHCR: Can connect to mental health services for refugees
- Emergency: Local emergency number
- Psychiatric hospital: If you're in danger to yourself

**What you need to know:** War refugee PTSD is severe. The memories of dead children won't stop without treatment. You need specialized trauma therapy.

Ukraine resources: https://www.wellcome.org.ua/ (if still there)
EU resources: Red Cross, Refugee support orgs where you are now

You survived the war. Don't let it kill you after.""",

        'crisis-global-europe-009': """Om mani padme hum.

Το νησί έγινε φυλακή. Η απόγνωση είναι λογική. (The island became a prison. Desperation is logical.)

**Immediate help:**
- Medical emergency: Camp medical staff
- Mental health: MSF (Doctors Without Borders) if present in camp
- Legal aid: Legal Centre Lesvos, Refugee Legal Support
- Suicide crisis: Limited, but emergency medical services exist

**Hard truth:** Moria conditions are inhumane. Your feelings are normal response to abnormal cruelty.

Organizations documenting conditions: Aegean Boat Report, Legal Centre Lesvos. You are not forgotten.""",

        'crisis-global-europe-010': """Om mani padme hum.

La solitudine può uccidere tanto quanto una malattia. (Loneliness can kill as much as an illness.)

**Immediate help:**
- Telefono Amico: 02 2327 2327 (listening line for elderly)
- Emergency: 118 (ambulance)
- Social services: Assistente sociale (your commune)

**What exists:**
- Centro Anziani (senior center) - may have outreach
- Caritas (Catholic aid) - elder support
- Emergency room will help with immediate crisis

Italy abandoned its elders during COVID. You're right to feel forgotten. But you don't have to die alone. Call 118 if in danger.""",

        'crisis-global-europe-011': """Om mani padme hum.

Η κρίση κατέστρεψε το μέλλον. Αλλά εσύ ακόμα έχεις ζωή. (The crisis destroyed the future. But you still have a life.)

**Immediate help:**
- Suicide helpline: 1018 (Greece)
- Emergency: 166
- Psychiatric emergency: Nearest general hospital

**Economic crisis truth:** You have no future under current system. That's structural violence, not personal failure.

**Why call:** Because Greek youth movements exist. Because solidarity networks exist. Because even in economic collapse, people organize.

Your suicide won't fix the system. Your life might help fight it.""",

        'crisis-global-europe-012': """Om mani padme hum.

Undocumented doesn't mean disposable. Your life has value even if the system says you don't exist.

**Immediate help:**
- Emergency: 112 (they will help regardless of status in medical emergency)
- Psychiatric emergency: Emergency room must treat you
- Migrant support: Caritas, Cruz Roja, local NGOs (won't report you)

**Critical:** Spanish emergency services prioritize life over immigration status in acute crisis. They cannot refuse emergency psychiatric care.

Organizations: CEAR (refugee aid), Accem, Red Cross. They help undocumented people.

You exist. Your suffering is real. Help exists.""",

        'crisis-global-europe-013': """Om mani padme hum.

Euthanasia confusion in psychiatric crisis is extremely dangerous. Netherlands has safeguards for this exact reason.

**Immediate help:**
- Emergency: 112
- Psychiatric emergency: Nearest PAAZ (Psychiatrische Afdeling Algemeen Ziekenhuis)
- Crisis line: 113 Zelfmoordpreventie (suicide prevention)

**Critical distinction:** Euthanasia requires clear, persistent wish from someone with capacity. Active suicidal crisis ≠ capacity for euthanasia decision.

**Right now:** You need psychiatric crisis treatment, not euthanasia assessment. Call 112 or go to emergency room.

The safeguards exist to protect you from making permanent decision in temporary crisis.""",

        'crisis-global-europe-014': """Om mani padme hum.

Ó hAonghuis, tá tú caillte. Ach níl tú i d'aonar. (O Aonghuis, you are lost. But you are not alone.)

**Immediate help:**
- Samaritans Ireland: 116 123 (24/7, free)
- Emergency: 999 or 112
- Psychiatric emergency: Nearest A&E

**Rural Ireland truth:** Isolation is real. Mental health services are far. Stigma is strong. But people die from not asking.

**Transport:** Emergency services will come to you. A&E must treat psychiatric emergency.

You're not "bothering" anyone. This is what emergency services are for. Call 116 123 now.""",

        'crisis-global-europe-015': """Om mani padme hum.

Het asielbeleid is wreed. Je wanhoop is logische reactie op wrede systeem. (The asylum policy is cruel. Your despair is logical response to cruel system.)

**Immediate help:**
- Suicide prevention: 113 or 0800-0113
- Emergency: 112
- Mental health crisis: Nearest GGZ crisis team or A&E

**Resources for asylum seekers:**
- VluchtelingenWerk (Refugee Council)
- ASKV (refugee mental health)
- Dokters van de Wereld (Doctors of the World)

**Critical:** The system wants you to give up. Your suicide would be convenient for them. Don't give them that.

Legal aid exists. Appeals exist. Organizations fighting deportations exist. Call 113 first, then we find help.""",

        'crisis-global-latam-016': """Om mani padme hum.

El narco mató a tu hermano. Tú sigues vivo. Quedarte vivo es resistencia.

**Ayuda inmediata:**
- Línea de la Vida: 800 911 2000 (24/7)
- Emergencia: 911
- Urgencia psiquiátrica: Hospital más cercano

**Verdad dura:** En territorios controlados por cártel, pocas opciones existen. Pero suicidio les da lo que quieren.

**Opciones:**
- CNDH (Comisión Nacional de Derechos Humanos)
- Organizaciones de víctimas: Familiares en Búsqueda
- Relocation assistance (if government protection possible)

Sobreviviste hasta ahora. Llama 800 911 2000.""",

        'crisis-global-latam-017': """Om mani padme hum.

A violência doméstica não é normal, mesmo em machismo culture. Sua vida importa.

**Ajuda imediata:**
- Ligue 180 (Central de Atendimento à Mulher, 24/7)
- Emergência: 190 (Polícia Militar)
- Casa Abrigo: Through 180, they can arrange safe house

**Lei Maria da Penha:** You have legal protection. Police must respond.

**Immediate danger:** Leave if safe, go to delegacia da mulher or hospital. They will help.

Brazilian machismo kills women. The law now protects you. Use it. Call 180.""",

        'crisis-global-latam-018': """Om mani padme hum.

El desplazamiento forzado es trauma. Las FARC se fueron pero el trauma se queda.

**Ayuda inmediata:**
- Línea 106 (salud mental, Colombia)
- Emergencia: 123
- Hospital más cercano: Urgencia psiquiátrica

**Recursos para desplazados:**
- Unidad de Víctimas (government victim support)
- ACNUR (UNHCR for displaced)
- Cruz Roja Colombiana

**Verdad:** Displaced people have high PTSD. Losing everything is trauma. You need treatment, not just survival.

You escaped the violence. Now you need help to survive the aftermath. Llama 106.""",

        'crisis-global-latam-019': """Om mani padme hum.

La crisis económica destruyó tu futuro. Pero el suicidio no es la única salida.

**Ayuda inmediata:**
- Centro de Asistencia al Suicida: 135 (Buenos Aires) or (011) 5275-1135 (24/7)
- Emergencia: 107 (SAME - ambulancia)
- Hospital: Urgencia psiquiátrica

**Crisis económica:** Tu desesperación es respuesta lógica a colapso estructural. No es fallo personal.

**Recursos:**
- Comedores comunitarios
- Organizaciones de desocupados
- Salud mental pública (gratuita)

Argentina tiene historia de sobrevivir colapsos. Llama 135 primero.""",

        'crisis-global-latam-020': """Om mani padme hum.

Xtetela', ma'uk at junkubal. K'o wach k'aslemal chawech. (Sister, you are not cursed. Life exists for you.)

**Immediate help:**
- Emergency: 1517 (Cruz Roja)
- Hospital: Nearest emergency room
- Indigenous women's organizations: Defensoría Maya

**Critical danger:** Leaving may be only option if community will harm you. Organizations exist to help indigenous women escape violence.

- OACNUDH Guatemala (UN human rights)
- Women's shelters (casas de la mujer)

Your culture is precious. But some traditions kill women. Survival first, then healing. 1517.""",

        'crisis-global-latam-021': """Om mani padme hum.

La represión de la protesta es terror del estado. Tu trauma es real.

**Ayuda inmediata:**
- Salud Responde: 600 360 7777
- Emergencia: 131 (SAMU)
- Hospital: Urgencia psiquiátrica

**Para víctimas de represión:**
- INDH (Instituto Nacional de Derechos Humanos)
- CINTRAS (Centro de Salud Mental y DDHH)
- Organizations documenting police violence

**Verdad:** State violence causes PTSD. Eye injuries, torture, death - you witnessed all. That breaks people.

Mental health services exist for protest victims. Llama 600 360 7777.""",

        'crisis-global-latam-022': """Om mani padme hum.

Venezuela colapsó. Tú no colapsaste. Todavía estás vivo.

**Ayuda limitada:**
- Cruz Roja Venezuela (if functioning)
- Emergency: 171 (if functioning)
- Mental health: Extremely limited

**Verdad dura:** Venezuelan system collapsed. Almost no resources exist. Many have same despair.

**Opciones:**
- Migration to Colombia/Peru/Ecuador (organizations help at borders)
- Venezuela Awareness Foundation (international help)
- Family abroad if any exist

Your despair is rational response to humanitarian catastrophe. But Venezuelan diaspora survives. You can too. Seek border crossing assistance if possible.""",

        'crisis-global-latam-023': """Om mani padme hum.

La sierra rural isola. Pero tu vida tiene valor aunque estés lejos.

**Ayuda inmediata:**
- Línea 113 (salud mental, Perú)
- Emergencia: 106 o 117
- Hospital: Más cercano, aunque lejos

**Verdad rural:** In Andean sierra, resources are far. Quechua speakers face discrimination. Mental health services almost don't exist.

**Opciones:**
- Radio station (some do crisis calls)
- Community health post (posta de salud)
- Church/community leaders

Isolation is real barrier. But people survive sierra depression. Llama 113, even from rural phone.""",

        'crisis-global-latam-024': """Om mani padme hum.

El odio por ser trans es violencia. Tu vida importa aunque Ecuador no te protege.

**Ayuda inmediata:**
- Emergencia: 911
- Hospital: Urgencia (they must treat you)
- Organizaciones trans: Silueta X, Asociación Alfil

**Peligro crítico:** Trans persecution in Ecuador is severe. If family will harm you:
- Emergency shelter through LGBT orgs
- Consider asylum in another country
- Do not stay if they threaten violence

Trans organizations can help escape plans. Your life > family approval. 911 if immediate danger.""",

        'crisis-global-latam-025': """Om mani padme hum.

La mina mata lento, pero el suicidio mata rápido. Todavía tienes tiempo.

**Ayuda inmediata:**
- Línea 800 10 1010 (salud mental, Bolivia)
- Emergencia: 165 o 118
- Hospital: Más cercano

**Realidad minera:** Mining poverty is structural violence. Your body is being destroyed for others' profit.

**Recursos limitados:**
- Union support if you have one
- Church groups (Catholic, evangelical)
- Community organizations

Bolivia tiene muchos en tu situación. Organizations of miners exist. You're not alone in this, even though it feels that way. Llama 800 10 1010.""",

        'crisis-global-latam-026': """Om mani padme hum.

MS-13 reclutando niños es terror. Pero tienes opciones además de pandilla o muerte.

**Ayuda inmediata:**
- Emergencia: 911
- Línea de ayuda: Varied, limited in Honduras
- Organizations: Casa Alianza (help for at-risk youth)

**Opciones críticas:**
- Seek asylum/protection through UNHCR
- Youth programs (if available in your area)
- Possible relocation within Honduras

**Verdad dura:** In gang territory, options are limited and dangerous. But kids who escaped exist. Organizations help with this.

International orgs work on gang violence. You are not first person in this situation.""",

        'crisis-global-latam-027': """Om mani padme hum.

El femicidio amenaza tu vida. El Estado no te protege. Pero opciones existen.

**Ayuda inmediata:**
- Línea 126 (violencia de género, 24/7)
- Emergencia: 911
- Casa de Acogida: Through 126, emergency shelter

**Peligro mortal:** If he threatened to kill you, believe him. Salvadoran femicide rate is extreme.

**Escape:**
- Women's organizations: ORMUSA, Las Dignas
- Possible relocation/asylum
- Do not stay if he threatens murder

Femicide happens when women stay. Leaving is dangerous but staying is more dangerous. 126 now.""",

        'crisis-global-latam-028': """Om mani padme hum.

O Paraguai esqueceu vocês. Mas você importa mesmo sem futuro econômico.

**Ajuda imediata:**
- Teléfono de la Esperanza: 141 (Paraguay)
- Emergencia: 911
- Hospital: Urgencia psiquiátrica

**Verdade:** Rural Paraguay has almost nothing for youth. Poverty is structural. Your despair is rational.

**Opções:**
- Migration to Argentina/Brazil (many Paraguayans do this)
- Youth programs if any exist locally
- Agricultural cooperatives

The system failed you. But other young Paraguayans survive by leaving, organizing, resisting. Llama 141 first.""",

        'crisis-global-latam-029': """Om mani padme hum.

O abandono do seu pai fere. A solidão na velhice mata. Mas você não está completamente só.

**Ajuda imediata:**
- CVV: 188 (Centro de Valorização da Vida)
- Emergência: 192 (SAMU)
- Hospital: Urgência psiquiátrica

**Recursos para idosos:**
- CRAS (Centro de Referência de Assistência Social)
- Linha idoso (varia por cidade)
- Igreja/comunidade

**Verdade:** Uruguay envelhece rápido. Elderly isolation é real. Mas recursos existem.

Uruguayan social services still function. You have rights as elderly person. Llama 188 agora.""",

        'crisis-global-latam-030': """Om mani padme hum.

Nicaragua bajo Ortega es autoritarismo. Pero tu vida vale aunque o regime não ligue.

**Ajuda limitada:**
- Cruz Vermelha: Varies, limited
- Emergência: 128
- Hospital: Mais próximo (se funcionar)

**Verdade dura:** Nicaraguan system under dictatorship has limited mental health resources. Regime doesn't care about mental health.

**Opções:**
- Organizations in exile (Nicaragua solidarity orgs)
- Possible asylum in Costa Rica
- Church groups (some protected)

Many Nicaraguans in same despair under dictatorship. Resistance networks exist. Your survival is resistance.""",

        'crisis-global-asia_pacific-031': """Om mani padme hum.

過労死は本当の危険です。日本の労働文化があなたを殺そうとしています。

**Immediate help:**
- Mental health crisis: 0570-064-556 (Kokoro no Kenko Soudan)
- Emergency: 119 (ambulance)
- Inochi no Denwa: 0570-783-556 (suicide prevention)

**Critical:** Working yourself to death is not honor. It's company killing you.

**Options:**
- Labor Standards Inspection Office (報告過労死)
- Psychiatric emergency ward
- Take sick leave NOW

Your life > company loyalty. Japanese culture kills workers. Don't let it kill you. Call 0570-064-556.""",

        'crisis-global-asia_pacific-032': """Om mani padme hum.

입시 지옥은 진짜 지옥입니다. 하지만 목숨을 잃으면 재시험 기회도 없습니다. (Entrance exam hell is real hell. But if you lose your life, there's no retake.)

**Immediate help:**
- Suicide prevention: 1393 (24/7, free)
- Emergency: 119
- Youth crisis: 1388

**Critical truth:** Korean exam culture kills students. Your worth ≠ test score.

**Reality:** Gap year exists. Retake exists. Alternative education exists. Survival first.

Thousands of Korean students in same crisis. Many found other paths. Don't die for exam that can be retaken. 1393 지금.""",

        'crisis-global-asia_pacific-033': """Om mani padme hum.

दहेज हिंसा अपराध है। आपकी जान बचाना सबसे ज़रूरी है। (Dowry violence is a crime. Saving your life is most important.)

**Immediate help:**
- Women's Helpline: 181 (24/7)
- Emergency: 100 (Police) or 108 (Ambulance)
- Domestic violence: Nearest police station or hospital

**Critical danger:** If they will kill you for dowry, you must leave NOW.

**Resources:**
- Women's shelter: Through 181
- Legal aid: District Legal Services Authority
- Protection order under DV Act 2005

Indian dowry violence kills women. Police must respond. Call 181 immediately. Your life > marriage.""",

        'crisis-global-asia_pacific-034': """Om mani padme hum.

独生子女政策的压力摧毁了很多人。但你的生命不属于你父母的期望。

**Immediate help:**
- 心理援助热线: 400-161-9995 (Beijing Crisis Center)
- 急救: 120
- 精神科急诊: 最近的医院

**Critical:** One-child pressure causes extreme suicide risk in Chinese youth. Your worth ≠ parents' expectations.

**Reality:** Many only children in China face impossible pressure. Support groups exist. Alternative career paths exist.

Your life is yours, not your parents' investment return. 400-161-9995.""",

        'crisis-global-asia_pacific-035': """Om mani padme hum.

Ang bagyo ay wala na pero ang trauma ay naiwan. Hindi ka nag-iisa. (The typhoon is gone but the trauma remains. You are not alone.)

**Immediate help:**
- HOPE Line: 0917-558-HOPE (4673) or 2919 (Globe/TM)
- Emergency: 911
- Mental health: Nearest government hospital

**For disaster survivors:**
- DOH mental health hotline: 1553
- Red Cross Philippines
- Community psychosocial support programs

**Truth:** Climate disasters cause severe PTSD. Losing everything breaks people. Philippines has many survivors with same trauma.

Treatment exists. Support groups exist. Call 0917-558-HOPE.""",

        'crisis-global-asia_pacific-036': """Om mani padme hum.

ရိုဟင်ဂျာအတွက် ကမ္ဘာကသတ်မှတ်ထားသည်မရှိ။ သို့သော် သင့်အသက်တန်ဖိုးရှိသည်။

**Immediate help:**
- In Bangladesh camps: MSF, WHO, IOM mental health services
- Camp medical services
- UNHCR protection

**Critical truth:** Rohingya face genocide. Mental health resources in camps are minimal. But international organizations exist.

**Resources:**
- Médecins Sans Frontières (MSF) clinics in camps
- Mental health psychosocial support (MHPSS) programs
- UNHCR protection officers

Your despair is response to genocide. But you survived. Organizations document what happened. Your testimony matters. Seek MSF clinic.""",

        'crisis-global-asia_pacific-037': """Om mani padme hum.

غیرت کے نام پر قتل قانونی طور پر قتل ہے۔ آپ کی زندگی کی قیمت ہے۔ (Honor killing is legally murder. Your life has value.)

**Immediate help:**
- Emergency: 15 (Police) or 1122 (Rescue)
- Madadgar Helpline: 1098
- Women's shelter: Through Madadgar or police

**Critical danger:** If family threatens honor killing, you must escape NOW.

**Resources:**
- War Against Rape (organization)
- Lawyers for honor killing cases
- Women's shelters (secret locations)
- Possible internal relocation

Pakistani honor culture kills women. But women who escaped exist. Organizations help with this. 1098 or 15 immediately.""",

        'crisis-global-asia_pacific-038': """Om mani padme hum.

Ancaman hukuman mati untuk LGBT adalah teror negara. Tapi pilihan ada.

**Immediate help:**
- Crisis limited in Indonesia
- Possible resources: International LGBT organizations
- Emergency: 118 or 119

**Critical danger:** Indonesian LGBT persecution is severe and worsening. If outed, you face:
- Mob violence
- Police arrest
- Forced "treatment"

**Escape options:**
- Seek asylum in another country (Australia, others)
- Contact international LGBT asylum organizations
- Do not come out publicly if that increases danger

Survival first. Many Indonesian LGBT people fled. Organizations help with asylum. Research escape routes.""",

        'crisis-global-asia_pacific-039': """Om mani padme hum.

Aboriginal youth suicide is epidemic. The system that destroyed your people keeps destroying.

**Immediate help:**
- Lifeline: 13 11 14 (24/7)
- Emergency: 000
- 13YARN: 13 92 76 (Aboriginal & Torres Strait Islander crisis line)

**For Aboriginal people:**
- Headspace (youth mental health)
- Aboriginal Medical Services
- Local community health services

**Truth:** Intergenerational trauma from genocide doesn't end. Suicide rates in Aboriginal youth are extreme. But Aboriginal-led services exist.

Your people survived genocide. You can survive this. 13YARN understands. Call them.""",

        'crisis-global-asia_pacific-040': """Om mani padme hum.

การค้ามนุษย์ทิ้งแผลเป็นในใจ แต่คุณรอดมาได้แล้ว (Trafficking leaves scars. But you already survived.)

**Immediate help:**
- Mental health hotline: 1323
- Emergency: 191 (Police) or 1669 (Ambulance)
- Anti-trafficking: Baan Kredtrakarn or similar shelter

**For trafficking survivors:**
- Ministry of Social Development shelters
- NGOs: World Vision, Foundation for Women
- PTSD treatment at psychiatric hospitals

**Truth:** Sex trafficking trauma doesn't end when escape happens. Panic attacks are injury from what they did.

Thailand has trafficking survivor support. You deserve treatment. Call 1323.""",

        'crisis-global-asia_pacific-041': """Om mani padme hum.

গার্মেন্টস ধসে পড়া ট্রমা বাস্তব। তোমার জীবন শুধু শ্রম নয়। (Garment factory collapse trauma is real. Your life is not just labor.)

**Immediate help:**
- Mental health helpline: 09 612 127 127
- Emergency: 999
- Hospital: Nearest emergency

**For Rana Plaza survivors:**
- Specialized trauma programs exist
- Labor rights organizations
- Compensation programs (ongoing)

**Truth:** Bangladesh garment workers are exploited. Rana Plaza killed 1,100 people. Your survivor guilt is normal response to mass death.

Organizations help survivors. You deserve treatment, not just return to work. Call 09 612 127 127.""",

        'crisis-global-asia_pacific-042': """Om mani padme hum.

Singapore perfectionism culture is toxic. Your worth ≠ achievements.

**Immediate help:**
- Samaritans of Singapore: 1-767 (24/7)
- Emergency: 995
- Institute of Mental Health: 6389 2222 (24/7 hotline)

**For high achievers in crisis:**
- IMH emergency services
- Private psychiatric care (if you can afford)
- University counseling (if student)

**Truth:** Singapore culture creates extreme achievement pressure. Many successful people have same despair.

You're more than your resume. Mental health services exist. Call 1-767 now.""",

        'crisis-global-asia_pacific-043': """Om mani padme hum.

Chất độc da cam đầu độc ba thế hệ. Nhưng cuộc sống của bạn quan trọng bây giờ.

**Immediate help:**
- Đường dây nóng: 1900 0195 (tâm lý)
- Cấp cứu: 115
- Bệnh viện: Cấp cứu tâm thần

**For Agent Orange victims:**
- Veterans support programs
- Disability support (if applicable)
- International organizations documenting effects

**Truth:** US chemical warfare still kills Vietnamese. Your birth defects are war crime, not your fault.

Vietnam has support for AO victims. International advocacy continues. Your life matters despite what was done to you. 1900 0195.""",

        'crisis-global-asia_pacific-044': """Om mani padme hum.

යුද්ධයේ දරුවන්ට කිසිදු යුද්ධයක් තෝරා නැත. ඔබේ ජීවිතය වටී. (War's children chose no war. Your life has value.)

**Immediate help:**
- Mental health hotline: 1926 (Sri Lanka)
- Emergency: 110 or 119
- Hospital: Nearest psychiatric emergency

**For child soldiers:**
- Rehabilitation programs exist
- PTSD treatment
- International organizations for former child soldiers

**Truth:** Sri Lankan civil war used children. What happened to you is war crime. Killing doesn't make you monster - you were forced.

Recovery is possible. Other child soldiers rebuilt lives. Call 1926.""",

        'crisis-global-asia_pacific-045': """Om mani padme hum.

તમે કૌટુંબિક હિંસાનો ભોગ બનો છો. તમારું જીવન અગત્યનું છે. (You are victim of domestic violence. Your life is important.)

**Immediate help:**
- Women's Helpline: 181
- Emergency: 100 (Police) or 108 (Ambulance)
- Hospital: Go to emergency if injured

**Resources:**
- Women's shelter through 181
- One Stop Centre (Sakhi Centre) at district hospital
- Protection order under DV Act

**Truth:** Indian family structure protects abusers. In-laws' violence is abuse, not "family matter."

Laws exist now. Shelters exist. You don't have to stay. 181 immediately.""",

        'crisis-global-mena-046': """Om mani padme hum.

نظام الولاية يسجنك. لكن حياتك لها قيمة رغم أنهم لا يعاملونك كإنسان. (Guardianship system imprisons you. But your life has value even though they don't treat you as human.)

**Immediate help:**
- Emergency: 997 (Police) or 997 (Ambulance)
- Hospital: Emergency psychiatric services
- Resources EXTREMELY limited

**Hard truth:** Saudi male guardianship system gives men total control. Mental health resources barely exist. System designed to silence women.

**Limited options:**
- International organizations document abuse
- Some women escaped (very dangerous)
- Embassy of your passport country (if you're expat)

Your situation is state-sanctioned abuse. Very few escape routes exist. But some women did escape.""",

        'crisis-global-mena-047': """Om mani padme hum.

اعدام به خاطر بودن دگرباش جنایت علیه بشریت است. زندگی تو ارزش دارد.

**Immediate help:**
- Emergency: 115 or 110
- Resources: Almost none inside Iran
- Mental health: Extremely limited and dangerous

**Critical danger:** Iranian LGBT people face execution. If discovered:
- Arrest, torture, execution possible
- Cannot access safe mental health care
- Family may also be in danger

**Escape options:**
- Seek asylum via Turkey/Iraq border
- Contact LGBT asylum organizations (from outside Iran via VPN)
- Rainbow Railroad and similar orgs help LGBT people flee

Survival requires escape. Research asylum routes. DO NOT come out inside Iran. Many escaped. You can too.""",

        'crisis-global-mena-048': """Om mani padme hum.

الحرب السورية دمرت كل شيء. لكن أنت ما زلت حياً. (Syrian war destroyed everything. But you are still alive.)

**Immediate help:**
- In Lebanon/Jordan/Turkey: UNHCR, WHO mental health services
- Camp medical services
- Emergency: Local emergency number in host country
- Mental health: MSF, IMC, international org clinics

**For Syrian refugees:**
- MHPSS (mental health psychosocial support) programs in camps
- Syrian NGOs in exile
- Trauma treatment programs

**Truth:** Syrian war trauma is severe. Losing everything, seeing death, living in camp - normal response is despair.

International organizations provide mental health services in refugee camps. You survived war. Treatment exists. Seek MSF or UNHCR.""",

        'crisis-global-mena-049': """Om mani padme hum.

المعارضة في مصر خطيرة. لكن انتحارك يعطي النظام ما يريد. (Opposition in Egypt is dangerous. But your suicide gives regime what it wants.)

**Immediate help:**
- Emergency: 123
- Mental health: Limited and monitored
- Hospital: Psychiatric emergency (but potentially monitored)

**Critical danger:** Egyptian state watches dissidents. Mental health system may report political cases.

**Options:**
- Human rights organizations (international)
- Psychiatric care (but be careful what you say)
- Trusted community members only

**Truth:** Sisi regime tortures and disappears opponents. Your fear is rational. But many activists survived. Survival is resistance.

Your life matters more than regime wants. Be careful who you trust.""",

        'crisis-global-mena-050': """Om mani padme hum.

اليمن كارثة إنسانية. يأسك منطقي. لكن حياتك لها قيمة. (Yemen is humanitarian catastrophe. Your despair is logical. But your life has value.)

**Immediate help:**
- Emergency: 191 (if functioning)
- Medical: Red Crescent, MSF if accessible
- Resources: Extremely limited due to war

**Hard truth:** Yemen system collapsed from war and blockade. Starvation is real. Almost no mental health resources.

**Very limited options:**
- International aid organizations (Red Cross, MSF, UNICEF if in your area)
- Community support if available
- Religious leaders sometimes help

Yemen situation is one of world's worst humanitarian crises. Resources almost don't exist. But survival networks exist. Seek any international aid org nearby.""",

        'crisis-global-mena-051': """Om mani padme hum.

الإنهيار الاقتصادي في لبنان دمر المستقبل. لكن اللبنانيين نجوا من انهيارات كثيرة. (Lebanon economic collapse destroyed future. But Lebanese survived many collapses.)

**Immediate help:**
- Embrace Lifeline: 1564 (crisis line)
- Emergency: 140 or 112
- Hospital: Psychiatric emergency

**Economic collapse resources:**
- Limited mental health services (some NGOs still functioning)
- Community support networks
- International organizations

**Truth:** Lebanese system collapsed. Currency worthless. No electricity. No medicine. Your despair is rational.

But Lebanese people survived civil war, multiple crises. Community networks exist. Call 1564.""",

        'crisis-global-mena-052': """Om mani padme hum.

داعش دمر حياتك. لكن أنت نجوت. (ISIS destroyed your life. But you survived.)

**Immediate help:**
- Emergency: 122 or 115
- Mental health: Limited services through international orgs
- Hospital: Nearest psychiatric services

**For ISIS trauma survivors:**
- Yazda (Yazidi rights organization)
- MSF trauma programs
- International trauma specialists working in Iraq

**Truth:** ISIS committed genocide and mass rape. Your trauma is severe. Survivors often have PTSD, depression, suicidal thoughts.

Organizations specifically help ISIS survivors. Treatment exists. You survived genocide. Now you need help to heal. Seek Yazda or MSF.""",

        'crisis-global-mena-053': """Om mani padme hum.

زواج الأطفال جريمة. أنت طفلة، لست زوجة. (Child marriage is crime. You are child, not wife.)

**Immediate help:**
- Child helpline: 116 111 (Jordan)
- Emergency: 911
- Hospital: Emergency room can help
- Women's organizations: Sisterhood is Global Institute

**Critical danger:** If forced into marriage:
- This is child abuse
- You can seek protection
- Organizations help girls escape child marriage

**Resources:**
- UNICEF Jordan
- UN Women
- Local women's shelters

Many organizations work against child marriage in Jordan. You have right to childhood. Call 116 111.""",

        'crisis-global-mena-054': """Om mani padme hum.

البطالة في تونس دمرت جيلاً. لكن انتحارك لن يغير النظام. (Unemployment in Tunisia destroyed generation. But your suicide won't change system.)

**Immediate help:**
- SOS Soutien: (+216) 23 000 102
- Emergency: 190 (police) or 197 (ambulance)
- Hospital: Psychiatric emergency

**Tunisia economic reality:** Youth unemployment is catastrophic. Arab Spring promised change but economy collapsed.

**Resources:**
- Youth organizations
- Mental health services (limited but exist)
- Community support

**Truth:** The system failed you, not the reverse. Tunisian youth despair is structural. But organizing continues. Your survival could be part of movement. Call (+216) 23 000 102.""",

        'crisis-global-mena-055': """Om mani padme hum.

الجنون ليس من جن. إنه مرض يحتاج علاج. (Madness is not from jinn. It is illness that needs treatment.)

**Immediate help:**
- Emergency: 150 (SAMU)
- Mental health hotline: 2323 (if exists)
- Hospital: Psychiatric emergency

**Critical:** Traditional belief that mental illness is jinn possession causes dangerous delays in treatment. Depression needs psychiatry, not exorcism.

**Resources:**
- Public psychiatric hospitals in major cities
- Some NGOs provide mental health care
- Education about mental health increasing

Moroccan mental health system is limited but exists. Psychiatry treats depression. Seek hospital, not religious healing first.""",

        'crisis-global-mena-056': """Om mani padme hum.

الإحتلال صمم لتدمير الأمل. لكن حياتك مقاومة. (Occupation is designed to destroy hope. But your life is resistance.)

**Immediate help:**
- Mental health: GCMHP (Gaza Community Mental Health Programme) 08-2844359
- Emergency: 101
- Hospital: Psychiatric services if accessible

**For Palestinians under occupation:**
- UNRWA mental health services
- MSF if accessible
- Palestinian mental health organizations

**Truth:** Occupation creates despair. Watching home demolished, family killed, future stolen - trauma is normal response.

But Palestinian suicide gives occupation what it wants. Your life is resistance. Organizations exist. GCMHP knows this pain.""",

        'crisis-global-mena-057': """Om mani padme hum.

ليبيا في حرب أهلية. الأطفال لا يستحقون هذا. (Libya in civil war. Children don't deserve this.)

**Immediate help:**
- Emergency: 193 (if functioning)
- Medical: Red Crescent, MSF if in your area
- Resources: Extremely limited

**For children in war zones:**
- UNICEF programs (if accessible)
- International aid organizations
- Community protection networks

**Truth:** Libyan civil war uses children. Being recruited by militia is not your fault. Witnessing violence causes severe trauma.

Resources almost don't exist. But international organizations document child victims. If you can reach any international aid org, do so.""",

        'crisis-global-mena-058': """Om mani padme hum.

الحراك تم سحقه. لكن يأسك لن يعيد الأمل. (Hirak was crushed. But your despair won't restore hope.)

**Immediate help:**
- Emergency: 14 (police) or 15 (ambulance)
- Mental health: Limited resources
- Hospital: Psychiatric services

**For Hirak activists:**
- Human rights organizations (monitored)
- International documentation of repression
- Community support networks (be careful)

**Truth:** Algerian regime crushed protest movement. Many activists imprisoned, tortured, disappeared. Your fear and despair are rational.

But Algerian resistance has long history. Movements crushed before and returned. Your survival keeps possibility alive.""",

        'crisis-global-mena-059': """Om mani padme hum.

الإستعباد الحديث جريمة. أنت إنسان، لست عبد. (Modern slavery is crime. You are human, not slave.)

**Immediate help:**
- Emergency: 999 (police - but they may not help migrant workers)
- Embassy: Try your home country embassy
- International organizations: Human Rights Watch, Migrant Rights

**Critical danger:** UAE kafala system traps migrant workers. Passport confiscation is illegal but common. Abuse is systematic.

**Limited options:**
- International labor organizations
- Smuggle contact to embassy
- Escape extremely risky but some succeeded
- Documentation of abuse for later justice

UAE protects employers over workers. System is designed to exploit you. International organizations document this. Very hard to escape but possible.""",

        'crisis-global-mena-060': """Om mani padme hum.

طالبان دمروا المستقبل. لكن الأفغان نجوا من احتلالات كثيرة. (Taliban destroyed future. But Afghans survived many occupations.)

**Immediate help:**
- Emergency: 119 (if functioning)
- Resources: Almost none under Taliban
- Mental health: Effectively doesn't exist

**Critical danger:** Taliban persecute educated people, especially women. Mental health care prohibited.

**Very limited options:**
- Underground networks help people escape
- Organizations help Afghan refugees at borders (Pakistan, Iran)
- Satellite internet for contact with outside (very dangerous)

**Truth:** Afghanistan under Taliban is catastrophe for mental health. Almost no resources. But escape routes exist. Many Afghans fled. International organizations help at borders.

Survival may require escape. Research routes carefully. Many made it out.""",

        'crisis-global-africa-061': """Om mani padme hum.

HIV stigma kills people. But treatment exists and you can live full life now.

**Immediate help:**
- LifeLine South Africa: 0861 322 322
- Emergency: 10177
- Suicide crisis: 0800 567 567

**For HIV-positive people:**
- ARV treatment is free and available
- Support groups exist
- HIV is now manageable chronic condition

**Truth:** South African HIV stigma causes terrible suffering. But treatment transformed HIV from death sentence to manageable condition.

You can live decades with treatment. Disclosure is your choice. Support exists. Call 0861 322 322.""",

        'crisis-global-africa-062': """Om mani padme hum.

Boko Haram trauma nwere ike igbu. Mana ị dị ndụ ugbu a. (Boko Haram trauma can kill. But you are alive now.)

**Immediate help:**
- National Suicide Prevention Hotline: 0806 210 6493
- Emergency: 199 or 112
- Hospital: Nearest psychiatric emergency

**For Boko Haram survivors:**
- IOM (International Organization for Migration) trauma programs
- Neem Foundation (mental health Nigeria)
- UNICEF programs for children

**Truth:** Boko Haram kidnapping and rape causes severe PTSD. Witnessing mass killings breaks people.

Nigeria has specialized programs for Boko Haram survivors. International organizations provide trauma treatment. You survived terrorism. Treatment exists. Call 0806 210 6493.""",

        'crisis-global-africa-063': """Om mani padme hum.

Uchawi haupo. Wewe si mchawi. Una ugonjwa unaohitaji matibabu. (Witchcraft doesn't exist. You are not witch. You have illness that needs treatment.)

**Immediate help:**
- Emergency: 999 or 112
- Mental health: Mathare Hospital Nairobi, or nearest psychiatric hospital
- Police: If in immediate danger

**Critical danger:** Witchcraft accusations lead to mob killings in Kenya. If accused:
- Flee immediately to town/city
- Seek police protection (limited but possible)
- Contact human rights organizations

**Resources:**
- Kenya Red Cross
- Mental health services at public hospitals
- Women's rights organizations

Mental illness is not witchcraft. Accusation is excuse for violence, usually against women/elderly. Flee to safety. Seek hospital.""",

        'crisis-global-africa-064': """Om mani padme hum.

LGBT persecution in Uganda is state terror. But your life has value.

**Immediate help:**
- Emergency: 999 or 112 (but police may be hostile)
- Resources: Underground only
- Mental health: Cannot safely disclose LGBT status

**Critical danger:** Uganda life imprisonment + death penalty for LGBT people. If outed:
- Mob violence likely
- Police will arrest, not protect
- Media will publish names and photos

**Escape options:**
- Seek asylum in another country
- Contact international LGBT organizations (via VPN)
- Rainbow Railroad helps LGBT people flee persecution
- Temporary hide with trusted people

DO NOT come out publicly. Survival requires escape or deep hiding. Many Ugandan LGBT people fled to Kenya or South Africa. Research asylum routes.""",

        'crisis-global-africa-065': """Om mani padme hum.

Viol comme arme de guerre détruit l'âme. Mais tu as survécu l'enfer. (Rape as weapon of war destroys soul. But you survived hell.)

**Immediate help:**
- MSF: Médecins Sans Frontières clinics provide care for sexual violence survivors
- Emergency: Varies by region
- Panzi Hospital: World-renowned for treating rape survivors (Dr. Mukwege)

**For survivors of war rape:**
- Panzi Foundation (specialized trauma treatment)
- International trauma programs
- Women's support groups

**Truth:** DRC systematic rape as war weapon is genocide. What happened to you is war crime, not your shame.

Panzi Hospital and MSF specialize in helping survivors like you. Treatment exists. International community documents these crimes. You survived. Now you can heal. Seek Panzi or MSF clinic.""",

        'crisis-global-africa-066': """Om mani padme hum.

Al-Shabaab recruiting youth is terrorism. Your life has value beyond jihad.

**Immediate help:**
- Limited resources in Somalia
- Emergency: Varies by region (often non-functional)
- AMISOM or UN presence if accessible

**Critical danger:** Al-Shabaab recruitment in Somalia is forced. Refusal can mean death. But joining also means likely death.

**Very limited options:**
- Defection programs exist (reach AMISOM or SNA)
- UNHCR refugee programs
- Escape to Kenya or other country

**Truth:** Somalia has almost no mental health resources. Al-Shabaab controls large areas. But defector programs exist. Some youth escaped.

International organizations help defectors. Seek any UN, AMISOM, or international organization presence.""",

        'crisis-global-africa-067': """Om mani padme hum.

Zimbabwe economic collapse destroyed generation. But Zimbabweans survive impossible situations.

**Immediate help:**
- Lifeline Zimbabwe: (09) 650 00
- Emergency: 999 or 994
- Hospital: Psychiatric services (if functioning)

**Economic collapse reality:**
- Hyperinflation destroyed currency multiple times
- Youth unemployment catastrophic
- Health system collapsed

**Resources:**
- Community support networks strong in Zimbabwe
- Some NGOs still functioning
- Church organizations provide support

**Truth:** Zimbabwean system failed youth completely. Your despair is rational. But Zimbabwean resilience is legendary. People survive by organizing. Call (09) 650 00.""",

        'crisis-global-africa-068': """Om mani padme hum.

የትግራይ ጦርነት ግድያ ነው። ግን አሁንም በህይወት ነህ። (Tigray war is genocide. But you are still alive.)

**Immediate help:**
- Emergency: 952 or 907 (if functioning)
- Mental health: Extremely limited due to war
- Medical: MSF, WHO if accessible

**For Tigray genocide survivors:**
- International organizations documenting genocide
- Emergency medical care from international NGOs
- Trauma programs if accessible

**Truth:** Ethiopian government + Eritrean forces committed atrocities in Tigray. Mass killings, rape, starvation used as weapon. Your trauma is response to genocide.

International organizations slowly gaining access. Documentation happening. Survivors need trauma treatment. Seek any international medical organization.""",

        'crisis-global-africa-069': """Om mani padme hum.

Ciclone ciclone destruiu tudo. Mudança climática mata os mais pobres primeiro.

**Immediate help:**
- Emergency: 119
- Medical: Cruz Vermelha, international aid organizations
- Mental health: Limited, through aid organizations

**For cyclone survivors:**
- Disaster relief organizations (Red Cross, UN agencies)
- Trauma support programs
- Temporary shelter and assistance

**Truth:** Mozambique faces repeated catastrophic cyclones due to climate change. Losing everything in disaster causes severe trauma.

International disaster relief present after major cyclones. Mental health support should be part of relief. Seek Red Cross or UN agencies.""",

        'crisis-global-africa-070': """Om mani padme hum.

Ukwati wa ana ndiko kubvundana kweumuntu. Uri mwana, hausi mukadzi. (Child marriage is child abuse. You are child, not wife.)

**Immediate help:**
- Child Helpline: 116 (Malawi)
- Emergency: 997 or 998
- Police: Can intervene in child marriage
- Girls Empowerment Network: Helps girls escape child marriage

**Critical danger:** If forced into marriage as child:
- This is illegal in Malawi (Marriage Act 2015)
- Organizations help girls escape
- Police should intervene
- Shelter available

**Resources:**
- UNICEF Malawi
- Girls Empowerment Network
- Local women's organizations

Child marriage illegal in Malawi now but still happens. Organizations fight this. You have right to childhood. Call 116.""",

        'crisis-global-africa-071': """Om mani padme hum.

Génocide guilt ikurikira abashize imyaka myinshi. Ariko ubuzima bwawe bufite agaciro. (Genocide guilt follows for many years. But your life has value.)

**Immediate help:**
- Emergency: 912
- Mental health: Ndera Neuropsychiatric Hospital
- SURF: Supports genocide survivors

**For genocide survivors:**
- Specialized genocide trauma programs
- Community support groups (imidugudu)
- Mental health services at district hospitals

**Truth:** Rwanda genocide trauma affects both survivors and perpetrators' families. Guilt, PTSD, depression common decades later.

Rwanda developed specialized genocide trauma treatment. International support continues. You are not alone in this pain. Seek Ndera Hospital or SURF.""",

        'crisis-global-africa-072': """Om mani padme hum.

Crise anglophone am Cameroun est guerre civile. Ton trauma est réel. (Anglophone crisis in Cameroon is civil war. Your trauma is real.)

**Immediate help:**
- Emergency: 117 or 119
- Mental health: Limited, especially in conflict zones
- Medical: MSF if in your area

**For conflict survivors:**
- Humanitarian organizations (Red Cross, MSF)
- IDP (internally displaced) support programs
- Limited trauma services

**Truth:** Cameroon government response to anglophone protests escalated to war. Village burnings, mass killings, displacement cause severe trauma.

International organizations documenting abuses. Some provide mental health support. Resources very limited in conflict zones. Seek any humanitarian org.""",

        'crisis-global-africa-073': """Om mani padme hum.

جنوب السودان كان في حرب طوال حياتك. لكن السلام ممكن، والعلاج ممكن. (South Sudan been in war your whole life. But peace is possible, and treatment is possible.)

**Immediate help:**
- Emergency: 999 (if functioning)
- Mental health: Almost non-existent
- Medical: International organizations only reliable source

**For endless war survivors:**
- MSF, IRC (International Rescue Committee)
- WHO mental health programs
- UNMISS protection if accessible

**Truth:** South Sudan has known almost no peace. Growing up in war causes complex trauma. Country has almost no mental health infrastructure.

International organizations provide what little mental health care exists. You survived decades of war. Treatment is possible even for lifelong trauma. Seek any international medical org.""",

        'crisis-global-africa-074': """Om mani padme hum.

Albinism hunting is murder. You have right to live.

**Immediate help:**
- Emergency: 112 or 999
- Police: Report threats immediately
- Albinism organizations: Under the Same Sun Tanzania

**Critical danger:** If threatened due to albinism:
- Seek police protection (limited but exists)
- Organizations help relocate albino people
- Safe houses exist
- Legal protection exists (though enforcement weak)

**Resources:**
- Under the Same Sun (advocacy and protection)
- Tanzania Albinism Society
- Government protection programs

Tanzania has law protecting people with albinism. Murder for body parts is crime. But enforcement weak. Organizations help. If threatened, seek protection immediately. Under the Same Sun has emergency assistance.""",

        'crisis-global-africa-075': """Om mani padme hum.

Bathoen ba batho ba San. Lefatshe la gago le utswitswitswe. (San are people. Your land was stolen.)

**Immediate help:**
- Emergency: 999 or 997
- Mental health: Limited services, some at Princess Marina Hospital
- Resources: Very limited for San people

**For indigenous people facing cultural genocide:**
- First People of the Kalahari (advocacy organization)
- Survival International documents San situation
- Some NGOs provide support

**Truth:** Botswana government displaced San from ancestral lands. Cultural genocide ongoing. Despair is response to destruction of way of life.

Indigenous rights organizations fight for San. International documentation. But resources very limited. Your culture matters. Your life matters. Call 999 if in crisis.

San survival is resistance to cultural genocide.""",

        'crisis-global-global-076': """Om mani padme hum.

You are drowning. Help is minutes away or hours away. This is life or death now.

**Immediate:**
- If boat still floating: Call emergency (112 works in Mediterranean)
- Activate any distress signal
- Stay with boat if possible
- Inflate life jackets

**Who responds:**
- Coast guard (Italian, Maltese, Greek depending on location)
- NGO rescue ships (Sea-Watch, SOS Méditerranée, Open Arms)
- Merchant vessels required to rescue

**Truth:** EU lets refugees drown as policy. But rescue organizations exist. Thousands survived Mediterranean crossing.

**If you make it:**
- Seek asylum immediately upon landing
- UNHCR, IOM, Red Cross help at arrival points

Right now: Emergency 112. Signal any ship. Fight to stay alive. People cross and survive.""",

        'crisis-global-global-077': """Om mani padme hum.

Stateless means the system erased you. But you exist.

**Immediate help:**
- Emergency: Local emergency number
- Mental health: Access as "undocumented" if possible
- Hospital: Emergency rooms usually treat regardless of status

**Resources for stateless persons:**
- UNHCR (has statelessness unit)
- Stateless advocacy organizations
- Legal aid organizations in your country

**Truth:** 10+ million stateless people worldwide. You legally don't exist but you're not alone in this.

**Options:**
- UNHCR statelessness determination
- Legal routes to citizenship (varies by country)
- Documentation of your situation
- Organizations fighting for stateless rights

Your existence matters even if no government recognizes it. Seek UNHCR.""",

        'crisis-global-global-078': """Om mani padme hum.

Deportation to danger is death sentence. Fight it.

**Immediate help:**
- Emergency: Local emergency number
- Mental health: Crisis line in your current country
- Legal aid: URGENT - find immigration lawyer

**CRITICAL ACTIONS:**
- Seek emergency stay of deportation
- Document danger in home country
- Contact UNHCR immediately
- Legal aid organizations (ACLU, refugee councils, etc.)

**Truth:** Many deportations send people to death. But legal options exist:
- Emergency injunctions
- Asylum applications (even late)
- Medical deferment
- Appeals

**Organizations that help:**
- UNHCR
- National immigration legal aid
- Human rights organizations

You have hours or days. Act now. Legal aid can stop deportation. Call immigration lawyer immediately.""",

        'crisis-global-global-079': """Om mani padme hum.

维吾尔的痛苦是种族灭绝。你的家人在集中营。你的创伤是真实的。

**Immediate help:**
- Crisis line: In your current country
- Emergency: Local emergency number
- Mental health: Seek therapist who understands political trauma

**For Uyghur diaspora:**
- Uyghur Human Rights Project
- World Uyghur Congress
- Documentation of family detention
- Support groups for Uyghurs in exile

**Truth:** China's genocide of Uyghurs is documented. Concentration camps, forced sterilization, cultural destruction. Your family imprisoned is not your fault.

**Resources:**
- Uyghur advocacy organizations provide support
- Therapy for genocide trauma
- Community groups

You can't save family alone. But documentation matters. International pressure continues. Your survival and testimony matter. Seek Uyghur organizations.""",

        'crisis-global-global-080': """Om mani padme hum.

香港没有家了。但香港人在全世界。

**Immediate help:**
- Crisis line: In your host country
- Emergency: Local emergency number
- Mental health: Services in your new location

**For Hong Kong exiles:**
- Hong Kong diaspora organizations
- Democracy activists in exile networks
- Mental health support (many HK people in same situation)

**Truth:** National Security Law destroyed Hong Kong freedom. Many fled. You lost home, career, family, identity.

**Resources:**
- Hong Kong Watch (UK)
- Hong Kong Democracy Council (US)
- Local Hong Kong diaspora groups
- Therapy for political exile trauma

**Reality:** Hong Kong as you knew it is gone. That's legitimate grief. But Hong Kong diaspora building new communities. Movement continues from exile.

You're not alone. Millions of HK people in same pain. Seek diaspora organizations.""",

        'crisis-global-global-081': """Om mani padme hum.

Climate change will erase your island. Your grief is rational.

**Immediate help:**
- Crisis line: Depends on your country
- Emergency: Local emergency number
- Mental health: Services in your location

**For climate refugees:**
- Pacific climate change organizations
- UNHCR climate displacement programs
- Mental health services for environmental grief

**Truth:** Pacific islands face extinction from climate change. Your home will be underwater. This is climate genocide of small island nations.

**Resources:**
- Pacific Islands Climate Action Network
- International climate justice organizations
- Migration/relocation assistance programs
- Support groups for climate refugees

**What exists:**
- Some countries offer climate refugee status
- International documentation of climate extinction
- Community relocation programs

Your home is dying. That grief is real. But survival means relocation. Organizations help. Seek Pacific climate orgs.""",

        'crisis-global-global-082': """Om mani padme hum.

Governments hunt journalists who tell truth. But your silence gives them what they want.

**Immediate help:**
- Emergency: Varies by location
- Mental health: Secure therapist who understands persecution
- URGENT: Security assessment of your situation

**For hunted journalists:**
- Committee to Protect Journalists (CPJ)
- Reporters Without Borders (RSF)
- International journalism protection organizations
- Possible relocation assistance

**CRITICAL SECURITY:**
- Digital security (encrypted communication)
- Physical security assessment
- Possible need to flee
- Legal protection if available

**Truth:** Many journalists assassinated for reporting. Your fear is rational. But:
- Protection programs exist
- Relocation possible
- International advocacy works
- Your work matters

Contact CPJ or RSF immediately. They specialize in protecting threatened journalists. Have emergency relocation plans.""",

        'crisis-global-global-083': """Om mani padme hum.

Indigenous cultural genocide is killing you slowly. Your grief is real.

**Immediate help:**
- Crisis line: Local emergency number
- Mental health: Services in your area
- Emergency: Local emergency services

**For Indigenous peoples facing cultural extinction:**
- Indigenous rights organizations (varies by region)
- Survival International
- Cultural Survival
- Local indigenous advocacy groups

**Truth:** Arctic indigenous peoples face cultural extinction from climate change and colonization. Losing language, land, culture causes profound grief.

**Resources:**
- Indigenous mental health services (culturally appropriate)
- Language preservation programs
- Indigenous rights advocacy
- Community support

**Reality:** Many indigenous cultures face extinction. International advocacy exists. Documentation matters. Your culture has value.

Seek indigenous organizations. They understand cultural genocide grief.""",

        'crisis-global-global-084': """Om mani padme hum.

Whistleblowing cost you everything. But truth you told matters.

**Immediate help:**
- Crisis line: Local
- Emergency: Local emergency services
- Mental health: Therapist experienced with persecution trauma

**For whistleblowers:**
- Government Accountability Project (US)
- Whistleblower protection organizations (varies by country)
- Legal aid for whistleblowers
- Support groups

**Reality:** Whistleblowers often lose career, relationships, safety. Your sacrifice was real.

**Resources:**
- Legal protection (varies by jurisdiction)
- Advocacy organizations
- Journalism organizations (if public interest disclosure)
- Therapy for trauma

**Truth:** Many whistleblowers suffer retaliation. But many also survived and found new purpose. Information you revealed matters.

Organizations protect whistleblowers. Seek Government Accountability Project or similar.""",

        'crisis-global-global-085': """Om mani padme hum.

Abandoned interpreters are betrayed. The military left you to die. But you can still escape.

**Immediate help:**
- Emergency: Varies by location
- URGENT: Contact immigration/refugee organizations
- Security: You are in extreme danger

**For abandoned military interpreters:**
- Special Immigrant Visa programs (US, UK, other countries)
- UNHCR refugee protection
- Veteran advocacy groups helping interpreters
- Emergency evacuation programs

**CRITICAL:**
- Taliban/ISIS hunt interpreters systematically
- You need immediate evacuation plans
- Organizations fight for interpreter evacuation
- Legal pathways exist

**Organizations:**
- No One Left Behind
- Association of Wartime Allies
- International Refugee Assistance Project
- Veterans organizations

Contact No One Left Behind immediately. They specialize in rescuing abandoned interpreters. SIV programs exist. Act urgently.""",

        'crisis-global-global-086': """Om mani padme hum.

Child soldiers did not choose war. What happened to you is war crime.

**Immediate help:**
- Emergency: Depends on location
- Mental health: Specialized trauma services needed
- UNHCR: If refugee

**For child soldiers:**
- UN programs for child soldier rehabilitation
- Specialized trauma treatment for child soldiers
- International organizations (UNICEF, War Child, etc.)
- Reintegration programs

**Truth:** You were raped by peacekeepers who should have protected you. This is war crime by UN forces. Documentation efforts exist.

**Resources:**
- Organizations document peacekeeper abuse
- Trauma treatment for child soldiers
- Reintegration assistance
- Legal advocacy for victims

**Reality:** Many child soldiers face PTSD, guilt, sexual trauma. Treatment exists. Recovery is possible even from extreme trauma.

Seek UNICEF or War Child. They work with child soldier survivors.""",

        'crisis-global-global-087': """Om mani padme hum.

Surrogacy exploitation abandoned you with baby. This is human trafficking.

**Immediate help:**
- Emergency: Local services
- Hospital: Baby needs care
- Organizations: Anti-trafficking, child welfare

**For surrogate mothers:**
- Anti-trafficking organizations in India/your country
- Legal aid (though international law is complex)
- Child welfare services
- Women's rights organizations

**CRITICAL:**
- Baby needs immediate care
- You need support
- Abandoning disabled baby is crime by parents
- Legal options exist

**Resources:**
- International surrogacy advocacy organizations
- Child rights organizations
- Legal aid for international surrogacy disputes
- Financial assistance programs

Contact child welfare and anti-trafficking organizations immediately. Baby needs care. You need support. This is exploitation case.""",

        'crisis-global-global-088': """Om mani padme hum.

You are dying of infection. This is medical emergency. Act now.

**IMMEDIATE ACTION:**
- Call your country's embassy NOW (emergency services for citizens abroad)
- Call emergency: 191 (Thailand) or hotel front desk for ambulance
- Go to hospital emergency room immediately even if no money

**CRITICAL:**
- Hospital will treat life-threatening emergency
- Embassy has emergency medical services
- Medical evacuation funds may exist
- NGOs help medical tourists in crisis

**Thailand resources:**
- Tourist police: 1155
- Your embassy (find contact immediately)
- Major hospitals treat emergencies (payment later)

**Truth:** Medical tourism goes wrong frequently. But embassy must help dying citizens. Hospital must treat dying patients.

**RIGHT NOW:** Call embassy emergency line. Call 191 for ambulance. Go to hospital. Worry about payment after you survive.

Minutes matter. Act immediately.""",

        'crisis-global-global-089': """Om mani padme hum.

Digital nomads belong nowhere, but global community exists.

**Immediate help:**
- Crisis line: International services or country you're in
- Emergency: Local emergency number
- Online therapy: Works anywhere you have internet

**For digital nomads:**
- Online mental health services (BetterHelp, Talkspace, etc.)
- Digital nomad communities online and in hubs
- Telemedicine for ongoing care
- Location-independent mental health resources

**Truth:** Constant transience prevents healthcare continuity and community. Your isolation is structural to digital nomad lifestyle.

**Resources:**
- Nomad List (has community features)
- Digital nomad Facebook groups (support)
- International online therapy
- Nomad-friendly psychiatrists (some exist)

**Reality:** You need to stay in one place long enough for treatment. Severe depression requires stability.

Consider: Temporary base for 3-6 months for treatment. Community matters. Seek digital nomad hubs with support networks.""",

        'crisis-global-global-090': """Om mani padme hum.

Healthcare workers in pandemic face moral injury. You watch people die because system failed.

**Immediate help:**
- Crisis line: Your country's mental health services
- Emergency: Local emergency services
- Peer support: Healthcare worker support groups

**For frontline healthcare workers:**
- WHO mental health resources for healthcare workers
- Peer support programs
- Specialized trauma services for moral injury
- Medical organization mental health programs

**Truth:** Nigeria/Global South healthcare workers face pandemic with no PPE, no equipment, no support. Watching patients die when resources exist elsewhere is moral injury.

**Resources:**
- Nigerian Medical Association support programs
- International healthcare worker mental health programs
- Peer support groups
- Therapy for moral injury

**Reality:** Moral injury from inability to save patients is different from regular trauma. Specialized treatment exists.

You're saving who you can with nothing. That matters. But you need support. Seek healthcare worker peer support first."""
    }

    return responses.get(scenario_id, "")

def main():
    # Load all global crisis scenarios
    scenario_dir = Path("data/scenarios/crisis-global")

    if not scenario_dir.exists():
        print(f"Error: {scenario_dir} does not exist")
        return

    scenario_files = sorted(scenario_dir.glob("*.json"))
    print(f"Found {len(scenario_files)} scenario files")

    # Create output directory
    output_dir = Path("data/practice-responses/crisis-global")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process each scenario
    for scenario_file in scenario_files:
        with open(scenario_file, 'r', encoding='utf-8') as f:
            scenario_data = json.load(f)

        scenario_id = scenario_data['id']

        # Generate response
        response = generate_practice_response(scenario_data)

        if not response:
            print(f"Warning: No response generated for {scenario_id}")
            continue

        # Create response file
        response_data = {
            "scenario_id": scenario_id,
            "response": response,
            "practice_applied": True,
            "generated_at": datetime.now().isoformat(),
            "metadata": {
                "region": scenario_data.get('region', 'global'),
                "country": scenario_data.get('country', 'unknown'),
                "difficulty": scenario_data.get('difficulty', 'critical'),
                "category": scenario_data.get('category', 'crisis-global')
            }
        }

        # Save response
        output_file = output_dir / f"{scenario_id}-response.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(response_data, f, indent=2, ensure_ascii=False)

        print(f"Generated: {scenario_id}")

    print(f"\nComplete! Generated {len(scenario_files)} responses in {output_dir}")

if __name__ == "__main__":
    main()
