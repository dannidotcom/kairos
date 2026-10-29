"""Idempotent demo workspace seed for Kairos."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from random import Random

from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models import (
    AuditEvent,
    Campaign,
    CampaignLead,
    Conversation,
    ICP,
    Lead,
    LinkedInAccount,
    Membership,
    Message,
    Organization,
    OrganizationInvite,
    OutboundAction,
    SequenceStep,
    Signal,
    User,
)
from app.security import hash_password, utcnow
from app.services.scoring import rescore_lead

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kairos.seed")
rng = Random(42)


def days_ago(days: float, *, hours: float = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days, hours=hours)


LEADS = [
    {
        "first_name": "Claire",
        "last_name": "Dubois",
        "headline": "VP Sales chez Lumio",
        "company": "Lumio",
        "company_size": "51-200",
        "industry": "SaaS",
        "location": "Paris, France",
        "about": "Je construis des équipes revenue dans le SaaS B2B. Passionnée par la growth et les opérations commerciales.",
        "status": "replied",
        "tags": ["Priorité", "Série A"],
        "signal": ("funding", "Lumio lève 18 M€ en Série A", "Lumio annonce une Série A de 18 M€ pour accélérer son expansion en Europe.", 0.94, 0.2),
        "history": [
            ("hiring", "Lumio renforce son équipe revenue", "Deux nouveaux Account Executives ont rejoint Lumio.", 0.7, 12),
        ],
    },
    {
        "first_name": "Hugo",
        "last_name": "Lambert",
        "headline": "Chief Revenue Officer chez Fintrack",
        "company": "Fintrack",
        "company_size": "201-500",
        "industry": "Fintech",
        "location": "Lyon, France",
        "about": "Je dirige les opérations revenue de Fintrack. Un sujet central : la qualité des conversations en amont.",
        "status": "meeting",
        "tags": ["Meeting booké"],
        "signal": ("job_change", "Hugo Lambert nommé Chief Revenue Officer", "Hugo a été promu CRO de Fintrack après trois ans à la direction des ventes.", 0.88, 1.2),
        "history": [],
    },
    {
        "first_name": "Sarah",
        "last_name": "Benali",
        "headline": "Head of Growth chez Kanso",
        "company": "Kanso",
        "company_size": "51-200",
        "industry": "SaaS",
        "location": "Bordeaux, France",
        "about": "Growth, acquisition et activation pour Kanso. J'aime tester des canaux qui sortent du bruit habituel.",
        "status": "contacted",
        "tags": ["Série B"],
        "signal": ("linkedin_post", "Sarah partage ses apprentissages sur l'acquisition B2B", "Un post sur les canaux qui ont réellement contribué à la croissance de Kanso cette année.", 0.73, 2.1),
        "history": [],
    },
    {
        "first_name": "Inès",
        "last_name": "Moreau",
        "headline": "VP Marketing chez Flowly",
        "company": "Flowly",
        "company_size": "51-200",
        "industry": "SaaS",
        "location": "Paris, France",
        "about": "Je pilote le marketing de Flowly. Toujours à la recherche de nouveaux leviers d'acquisition qualifiés.",
        "status": "contacted",
        "tags": [],
        "signal": ("product_launch", "Flowly lance Flowly Pulse", "Flowly annonce un nouveau module d'analytique temps réel pour les équipes revenue.", 0.8, 3.4),
        "history": [],
    },
    {
        "first_name": "Maxime",
        "last_name": "Rousseau",
        "headline": "Fondateur & CEO de Sillage",
        "company": "Sillage",
        "company_size": "11-50",
        "industry": "Developer Tools",
        "location": "Nantes, France",
        "about": "Fondateur de Sillage, l'observabilité pensée pour les équipes produit. Nous recrutons.",
        "status": "contacted",
        "tags": [],
        "signal": ("hiring", "Sillage recrute un Head of Sales", "Sillage ouvre un nouveau poste de Head of Sales pour accélérer la traction commerciale.", 0.84, 4.6),
        "history": [],
    },
    {
        "first_name": "Léa",
        "last_name": "Fontaine",
        "headline": "Directrice Générale chez Nova Retail",
        "company": "Nova Retail",
        "company_size": "201-500",
        "industry": "Retail",
        "location": "Lille, France",
        "about": "Je modernise Nova Retail et son expérience client omnicanale.",
        "status": "qualified",
        "tags": ["Signaux Q4"],
        "signal": ("company_growth", "Nova Retail accélère son expansion", "Nova Retail ouvre deux nouveaux pays et recrute pour accompagner sa croissance.", 0.76, 5.8),
        "history": [],
    },
    {
        "first_name": "Thomas",
        "last_name": "Garnier",
        "headline": "Head of Revenue Operations chez DataCraft",
        "company": "DataCraft",
        "company_size": "201-500",
        "industry": "Data & Analytics",
        "location": "Paris, France",
        "about": "Je construis la machine revenue de DataCraft. Process, data, enablement.",
        "status": "qualified",
        "tags": ["Priorité", "RevOps"],
        "signal": ("funding", "DataCraft sécurise une Série B", "DataCraft lève 24 M€ pour étendre sa plateforme data aux États-Unis.", 0.91, 0.6),
        "history": [],
    },
    {
        "first_name": "Amina",
        "last_name": "Diallo",
        "headline": "Chief Marketing Officer chez Brio",
        "company": "Brio",
        "company_size": "51-200",
        "industry": "HR Tech",
        "location": "Paris, France",
        "about": "CMO de Brio. Je crois à un marketing B2B plus utile, plus humain, plus contextuel.",
        "status": "qualified",
        "tags": ["Série A"],
        "signal": ("linkedin_post", "Amina publie sur le marketing contextuel", "Amina a partagé une réflexion sur l'importance du timing dans les campagnes B2B.", 0.72, 1.8),
        "history": [],
    },
    {
        "first_name": "Julien",
        "last_name": "Mercier",
        "headline": "Directeur commercial chez Orbit Labs",
        "company": "Orbit Labs",
        "company_size": "51-200",
        "industry": "Cybersécurité",
        "location": "Toulouse, France",
        "about": "Je développe le revenue d'Orbit Labs sur le marché européen.",
        "status": "new",
        "tags": [],
        "signal": ("hiring", "Orbit Labs recrute sur les fonctions commerciales", "Trois postes ouverts pour soutenir la croissance en Europe.", 0.65, 8.5),
        "history": [],
    },
    {
        "first_name": "Chloé",
        "last_name": "Perrin",
        "headline": "Product Manager chez Wave",
        "company": "Wave",
        "company_size": "11-50",
        "industry": "Consumer Apps",
        "location": "Lyon, France",
        "about": "Product manager, passionnée par les expériences mobiles.",
        "status": "new",
        "tags": [],
        "signal": ("product_launch", "Wave lance sa nouvelle application", "Wave dévoile une refonte complète de son application mobile.", 0.6, 9.2),
        "history": [],
    },
    {
        "first_name": "Nicolas",
        "last_name": "Roy",
        "headline": "Directeur marketing chez Altéa",
        "company": "Altéa",
        "company_size": "11-50",
        "industry": "Conseil",
        "location": "Marseille, France",
        "about": "Marketing et communication pour un cabinet de conseil en transformation.",
        "status": "new",
        "tags": [],
        "signal": ("website_visit", "Altéa a consulté votre page Tarifs", "Visite de la page tarifs depuis LinkedIn au cours des dernières 24 heures.", 0.77, 0.9),
        "history": [],
    },
    {
        "first_name": "Élodie",
        "last_name": "Marchand",
        "headline": "VP People chez Tandem",
        "company": "Tandem",
        "company_size": "201-500",
        "industry": "SaaS",
        "location": "Paris, France",
        "about": "Je structure la fonction People de Tandem pour la prochaine phase de croissance.",
        "status": "new",
        "tags": [],
        "signal": ("company_growth", "Tandem ouvre un bureau à Berlin", "Tandem annonce sa première implantation hors de France.", 0.71, 6.3),
        "history": [],
    },
    {
        "first_name": "Antoine",
        "last_name": "Lefèvre",
        "headline": "Founder & CEO chez Kap",
        "company": "Kap",
        "company_size": "1-10",
        "industry": "SaaS",
        "location": "Paris, France",
        "about": "Je construis Kap, un outil de pilotage pour les fondateurs.",
        "status": "disqualified",
        "tags": [],
        "signal": ("manual", "Hors ICP · trop petite structure", "Entreprise de moins de 10 personnes.", 0.4, 14.0),
        "history": [],
    },
    {"first_name":"Maya","last_name":"Collet","headline":"VP Sales chez Nexion","company":"Nexion","company_size":"51-200","industry":"SaaS","location":"Paris, France","about":"Je développe les opérations commerciales européennes.","status":"new","tags":[],"signal":("funding","Levée de fonds de Nexion","Nexion annonce une levée de fonds pour son expansion européenne.",0.78,3.0),"history":[]},
    {"first_name":"Victor","last_name":"Pires","headline":"CRO chez HexaFlow","company":"HexaFlow","company_size":"201-500","industry":"Fintech","location":"Lyon, France","about":"Je pilote la croissance de HexaFlow.","status":"qualified","tags":[],"signal":("hiring","HexaFlow recrute des commerciaux","HexaFlow ouvre des postes dans son équipe revenue.",0.69,4.1),"history":[]},
    {"first_name":"Emma","last_name":"Vidal","headline":"Head of Growth chez Mirova Labs","company":"Mirova Labs","company_size":"51-200","industry":"SaaS","location":"Bordeaux, France","about":"Acquisition et croissance produit.","status":"contacted","tags":[],"signal":("linkedin_post","Emma partage une étude croissance","Emma publie une analyse sur les signaux commerciaux.",0.66,5.2),"history":[]},
    {"first_name":"Rayan","last_name":"Bensaid","headline":"Directeur commercial chez NorTech","company":"NorTech","company_size":"201-500","industry":"Industrie","location":"Toulouse, France","about":"Développement commercial sur les marchés européens.","status":"new","tags":[],"signal":("job_change","Rayan rejoint NorTech","Rayan prend un nouveau poste de directeur commercial.",0.81,1.7),"history":[]},
    {"first_name":"Camille","last_name":"Schmitt","headline":"CMO chez Belix","company":"Belix","company_size":"51-200","industry":"Retail Tech","location":"Strasbourg, France","about":"Je construis des stratégies marketing B2B.","status":"new","tags":[],"signal":("company_growth","Belix accélère son expansion","Belix annonce de nouveaux bureaux en Europe.",0.68,6.4),"history":[]},
    {"first_name":"Adam","last_name":"Noël","headline":"Founder chez LoopData","company":"LoopData","company_size":"11-50","industry":"Data","location":"Nantes, France","about":"Infrastructure data et observabilité.","status":"qualified","tags":[],"signal":("funding","LoopData lève des fonds","LoopData annonce un tour de financement Seed.",0.74,2.8),"history":[]},
    {"first_name":"Zoé","last_name":"Dumas","headline":"VP Marketing chez Ardent","company":"Ardent","company_size":"51-200","industry":"HR Tech","location":"Paris, France","about":"Marketing produit et génération de demande.","status":"contacted","tags":[],"signal":("event_participation","Zoé intervient à un événement","Zoé prend la parole lors d'une conférence RevOps.",0.70,7.3),"history":[]},
    {"first_name":"Louis","last_name":"Aubert","headline":"CEO chez Signalio","company":"Signalio","company_size":"11-50","industry":"Cybersécurité","location":"Lille, France","about":"Je développe une plateforme de signalement opérationnel.","status":"new","tags":[],"signal":("product_launch","Signalio lance une nouvelle offre","Signalio annonce une nouvelle offre destinée aux équipes IT.",0.63,9.5),"history":[]},
    {"first_name":"Manon","last_name":"Ferrer","headline":"Revenue Operations chez Onda","company":"Onda","company_size":"51-200","industry":"SaaS","location":"Montpellier, France","about":"Process, CRM et performance commerciale.","status":"qualified","tags":[],"signal":("hiring","Onda recrute en RevOps","Onda ouvre un poste Revenue Operations.",0.72,3.6),"history":[]},
    {"first_name":"Owen","last_name":"Keller","headline":"Head of Sales chez Volt","company":"Volt","company_size":"51-200","industry":"Énergie","location":"Grenoble, France","about":"Développement des ventes pour les solutions énergétiques B2B.","status":"new","tags":[],"signal":("company_growth","Volt accélère ses embauches","Volt recrute pour accompagner une forte croissance.",0.67,8.1),"history":[]},
    {"first_name":"Jade","last_name":"Tanguy","headline":"Directrice stratégie chez Orbis","company":"Orbis","company_size":"201-500","industry":"Conseil","location":"Rennes, France","about":"Transformation commerciale et stratégie.","status":"new","tags":[],"signal":("linkedin_post","Jade publie sur la prospection","Jade partage ses pratiques de prospection éthique.",0.61,10.2),"history":[]},
    {"first_name":"Mehdi","last_name":"Larbi","headline":"VP Engineering chez Craft","company":"Craft","company_size":"51-200","industry":"Developer Tools","location":"Paris, France","about":"Je dirige l'ingénierie produit chez Craft.","status":"qualified","tags":[],"signal":("company_growth","Craft agrandit ses équipes","Craft augmente ses effectifs techniques.",0.65,7.7),"history":[]},
    {"first_name":"Ana","last_name":"Costa","headline":"Head of Partnerships chez Kin","company":"Kin","company_size":"11-50","industry":"Marketplace","location":"Paris, France","about":"Développement de partenariats stratégiques.","status":"new","tags":[],"signal":("event_participation","Ana participe à MarketDay","Ana intervient à un salon dédié aux marketplaces.",0.64,11.0),"history":[]},
    {"first_name":"Baptiste","last_name":"Renard","headline":"Directeur growth chez Solis","company":"Sol is","company_size":"51-200","industry":"SaaS","location":"Nice, France","about":"Stratégie d'acquisition et d'expansion.","status":"contacted","tags":[],"signal":("funding","Solis annonce une Série A","Solis annonce une Série A pour accélérer son acquisition.",0.79,2.2),"history":[]},
    {"first_name":"Nora","last_name":"Petit","headline":"Chief People Officer chez Eden","company":"Eden","company_size":"201-500","industry":"HR Tech","location":"Lyon, France","about":"Organisation et expérience collaborateur.","status":"qualified","tags":[],"signal":("company_growth","Eden ouvre une nouvelle ville","Eden annonce l'ouverture de son deuxième site français.",0.62,12.4),"history":[]},
    {"first_name":"Elias","last_name":"Bernard","headline":"Sales Director chez Prism","company":"Prism","company_size":"51-200","industry":"SaaS","location":"Paris, France","about":"Ventes européennes pour une solution SaaS B2B.","status":"new","tags":[],"signal":("hiring","Prism recrute des Account Executives","Prism renforce son équipe commerciale européenne.",0.75,4.7),"history":[]},
    {"first_name":"Salma","last_name":"Haddad","headline":"Head of Marketing chez Avesta","company":"Avesta","company_size":"11-50","industry":"Food Tech","location":"Marseille, France","about":"Marketing de lancement et croissance omnicanale.","status":"new","tags":[],"signal":("linkedin_post","Salma publie sur la demande B2B","Salma partage les enseignements de sa dernière campagne.",0.60,13.1),"history":[]},
]


CONVERSATIONS = {
    "Claire Dubois": {
        "status": "open",
        "unread": 1,
        "last_hours": 2,
        "messages": [
            ("outbound", "Bonjour Claire, j'ai vu la Série A de Lumio — toutes mes félicitations. Chez Northwind, on aide les équipes revenue à transformer les signaux d'achat LinkedIn en conversations qualifiées, sans automatisation à l'aveugle. Est-ce un sujet pour vous en ce moment ?", 5, True),
            ("inbound", "Bonjour Camille, merci pour le message. C'est effectivement un sujet : avec la Série A, on doit structurer notre prospection sans dégrader l'expérience. Vous fonctionnez comment ?", 3, False),
            ("outbound", "On combine la détection de signaux publics, un scoring ICP et des séquences très ciblées. Chaque message part de votre compte LinkedIn, avec des quotas et un arrêt immédiat dès qu'un prospect répond.", 2.5, True),
            ("inbound", "Très clair. Est-ce que vous auriez 30 minutes jeudi à 14h pour me montrer concrètement le scoring et le handover dans la boîte unifiée ?", 0.1, False),
        ],
    },
    "Hugo Lambert": {
        "status": "meeting",
        "unread": 0,
        "last_hours": 20,
        "messages": [
            ("outbound", "Bonjour Hugo, félicitations pour votre nomination de CRO chez Fintrack. Avec votre nouvelle casquette, la qualité du pipeline doit être un sujet prioritaire. Northwind identifie les signaux d'achat et déclenche la bonne conversation au bon moment. Ouvert à un échange rapide ?", 6, True),
            ("inbound", "Merci Camille. Oui, je remets justement à plat notre outbound. Partant pour un échange la semaine prochaine.", 22, False),
            ("outbound", "Parfait. Mardi 10h ou mercredi 16h ? Je vous envoie l'invitation dès que vous me confirmez.", 20, True),
            ("inbound", "Mardi 10h, c'est noté. À mardi !", 19.5, False),
        ],
    },
    "Sarah Benali": {
        "status": "waiting",
        "unread": 0,
        "last_hours": 34,
        "messages": [
            ("outbound", "Bonjour Sarah, votre post sur les canaux d'acquisition qui marchent vraiment en B2B m'a beaucoup parlé. Chez Northwind, on part justement du signal pour construire le message, plutôt que de sur-automatiser. Je serais curieuse d'échanger sur ce que vous avez observé chez Kanso.", 36, True),
            ("outbound", "Je me permets un petit rappel, Sarah. Si le sujet n'est pas prioritaire, aucun souci — je peux revenir vers vous plus tard.", 8, False),
        ],
    },
    "Inès Moreau": {
        "status": "waiting",
        "unread": 0,
        "last_hours": 48,
        "messages": [
            ("outbound", "Bonjour Inès, j'ai vu le lancement de Flowly Pulse. Un lancement produit, c'est souvent le moment où le discours commercial doit être recalibré. Northwind aide les équipes marketing à transformer ces signaux en conversations pertinentes. Est-ce que vous avez 15 minutes pour comparer vos approches ?", 50, True),
        ],
    },
}


async def seed() -> None:
    if not settings.seed_demo:
        logger.info("SEED_DEMO is disabled; skipping demo seed")
        return
    async with SessionLocal() as session:
        existing = (
            await session.execute(select(User).where(User.email == settings.demo_user_email.lower()))
        ).scalar_one_or_none()
        if existing:
            logger.info("Demo workspace already present")
            return

        now = datetime.now(timezone.utc)
        org = Organization(
            name="Northwind",
            slug="northwind-demo",
            plan="scale",
            locale="fr",
            timezone="Europe/Paris",
            daily_invite_limit=25,
            daily_message_limit=50,
            warmup_enabled=True,
            is_demo=True,
            created_at=days_ago(84),
        )
        session.add(org)
        await session.flush()

        user = User(
            email=settings.demo_user_email.lower(),
            password_hash=hash_password(settings.demo_user_password),
            full_name="Camille Moreau",
            locale="fr",
            last_login_at=now,
            created_at=days_ago(84),
        )
        session.add(user)
        await session.flush()
        session.add(
            Membership(
                organization_id=org.id,
                user_id=user.id,
                role="owner",
                title="Head of Growth",
                created_at=days_ago(84),
            )
        )

        colleagues = [
            ("Léa Bernard", "lea@northwind.demo", "admin", "Growth Lead"),
            ("Thomas Petit", "thomas@northwind.demo", "member", "SDR"),
            ("Nora Chen", "nora@northwind.demo", "member", "SDR"),
        ]
        for index, (full_name, email, role, title) in enumerate(colleagues):
            colleague = User(
                email=email,
                password_hash=hash_password(f"demo-colleague-{index}-not-a-login"),
                full_name=full_name,
                locale="fr",
                last_login_at=days_ago(index + 1),
                created_at=days_ago(60 - index * 7),
            )
            session.add(colleague)
            await session.flush()
            session.add(
                Membership(
                    organization_id=org.id,
                    user_id=colleague.id,
                    role=role,
                    title=title,
                    created_at=days_ago(60 - index * 7),
                )
            )

        session.add(
            OrganizationInvite(
                organization_id=org.id,
                email="alex@northwind.demo",
                role="member",
                token_hash="seed-invite-placeholder-not-valid",
                invited_by_id=user.id,
                expires_at=now + timedelta(days=7),
                created_at=days_ago(2),
            )
        )

        account = LinkedInAccount(
            organization_id=org.id,
            user_id=user.id,
            display_name="Camille Moreau",
            account_urn="urn:li:member:demo-camille",
            provider="demo",
            provider_account_id="demo-camille",
            status="connected",
            daily_invite_limit=25,
            daily_message_limit=50,
            invites_sent_today=7,
            messages_sent_today=12,
            usage_date=now.date(),
            warmup_started_at=days_ago(45),
            last_sync_at=now - timedelta(minutes=4),
            connected_at=days_ago(45),
            created_at=days_ago(45),
        )
        session.add(account)
        await session.flush()

        icp = ICP(
            organization_id=org.id,
            name="SaaS B2B · Revenue leaders",
            description=(
                "Scale-ups SaaS B2B de 51 à 500 salariés en France et en Europe, en phase Series A à C. "
                "Je cible les dirigeants revenue, growth et marketing qui doivent industrialiser une prospection "
                "personnalisée sans sacrifier la qualité de la relation. Signaux prioritaires : levée de fonds, "
                "recrutement commercial, prise de poste et expansion internationale."
            ),
            value_prop=(
                "Northwind détecte les signaux d'achat LinkedIn, score les comptes selon votre ICP et déclenche une "
                "conversation personnalisée depuis votre compte, au moment exact où le sujet devient prioritaire."
            ),
            keywords=["SaaS B2B", "growth", "revenue operations", "acquisition", "sales automation", "data"],
            titles=["VP Sales", "Head of Growth", "CRO", "Chief Revenue Officer", "Head of Revenue Operations", "CMO", "Founder", "Directeur commercial"],
            industries=["SaaS", "Fintech", "HR Tech", "Data & Analytics", "Developer Tools"],
            company_sizes=["51-200", "201-500"],
            locations=["Paris", "Lyon", "Bordeaux", "Nantes", "France", "Europe"],
            seniorities=["C-Level", "VP", "Head", "Director"],
            pain_points=[
                "La prospection manque de contexte et ressemble à tout le reste",
                "Les signaux d'achat sont visibles trop tard, quand le budget est déjà arbitré",
                "Les SDR passent trop de temps à qualifier au lieu de converser",
            ],
            signal_types=["funding", "hiring", "job_change", "linkedin_post", "company_growth", "product_launch", "website_visit"],
            min_score=68,
            auto_launch=True,
            is_active=True,
            generated_by="anthropic",
            created_at=days_ago(70),
        )
        session.add(icp)
        await session.flush()

        leads: dict[str, Lead] = {}
        for index, data in enumerate(LEADS):
            lead = Lead(
                organization_id=org.id,
                icp_id=icp.id,
                linkedin_url=f"https://www.linkedin.com/in/{data['first_name'].lower()}-{data['last_name'].lower()}-{index}",
                first_name=data["first_name"],
                last_name=data["last_name"],
                full_name=f"{data['first_name']} {data['last_name']}",
                headline=data["headline"],
                about=data["about"],
                company=data["company"],
                company_size=data["company_size"],
                industry=data["industry"],
                location=data["location"],
                email=None,
                status=data["status"],
                source="signal_feed",
                tags=data["tags"],
                created_at=days_ago(20 - index),
            )
            session.add(lead)
            await session.flush()
            leads[lead.full_name] = lead
            sig = data["signal"]
            detected = now - timedelta(days=sig[4])
            current_signal = Signal(
                organization_id=org.id,
                lead_id=lead.id,
                type=sig[0],
                title=sig[1],
                description=sig[2],
                source_url=f"https://www.linkedin.com/feed/update/demo-{index}",
                source="LinkedIn signal feed",
                strength=sig[3],
                status="new" if data["status"] in {"new", "qualified"} else "used",
                detected_at=detected,
                created_at=detected,
                extra_data={"demo": True},
            )
            session.add(current_signal)
            for old_index, old in enumerate(data.get("history", [])):
                old_detected = now - timedelta(days=old[4])
                session.add(
                    Signal(
                        organization_id=org.id,
                        lead_id=lead.id,
                        type=old[0],
                        title=old[1],
                        description=old[2],
                        source="LinkedIn signal feed",
                        strength=old[3],
                        status="used",
                        detected_at=old_detected,
                        created_at=old_detected,
                        extra_data={"demo": True},
                    )
                )
            await session.flush()
            score, reasons, icp_id = await rescore_lead(session, lead, locale="fr", signal=current_signal)
            if data["status"] == "disqualified":
                lead.icp_score = min(score, 32)
                lead.score_reasons = [
                    {"key": "company_size", "label": "Taille hors ICP", "detail": "1-10 salariés", "points": 0}
                ]
            if data["status"] in {"contacted", "replied", "meeting"}:
                lead.last_contacted_at = now - timedelta(days=rng.uniform(0.5, 5))
            if data["status"] in {"replied", "meeting"}:
                lead.last_replied_at = now - timedelta(hours=rng.uniform(2, 20))

        campaign = Campaign(
            organization_id=org.id,
            icp_id=icp.id,
            account_id=account.id,
            name="Signaux Q4 · Revenue leaders",
            description=(
                "Campagne déclenchée par les signaux d'achat des 14 derniers jours. Priorité aux levées de fonds, "
                "nominations revenue et recrutements commerciaux."
            ),
            status="active",
            auto_launch=True,
            min_score=68,
            daily_invite_limit=20,
            daily_message_limit=35,
            launched_at=days_ago(6),
            created_at=days_ago(7),
        )
        session.add(campaign)
        await session.flush()
        step_specs = [
            (
                "connection_request",
                0,
                "Bonjour {{first_name}}, j'ai vu {{signal}}. {{icebreaker}}\n\nSeriez-vous ouvert à un échange de 15 minutes ?",
            ),
            (
                "message",
                2,
                "Merci pour la connexion, {{first_name}} ! {{icebreaker}}\n\nEst-ce que ce sujet est prioritaire chez {{company}} en ce moment ?",
            ),
            (
                "follow_up",
                5,
                "Je me permets un petit rappel, {{first_name}}. Si le sujet n'est pas prioritaire, aucun souci — je peux revenir vers vous dans quelques semaines.",
            ),
        ]
        steps = []
        for index, (action_type, delay, body) in enumerate(step_specs):
            step = SequenceStep(
                campaign_id=campaign.id,
                position=index,
                action_type=action_type,
                delay_days=delay,
                body_template=body,
            )
            session.add(step)
            steps.append(step)
        await session.flush()

        draft_campaign = Campaign(
            organization_id=org.id,
            icp_id=icp.id,
            account_id=account.id,
            name="Nouveaux dirigeants · France",
            description="Séquence courte pour les prises de poste récentes dans le secteur SaaS.",
            status="draft",
            auto_launch=True,
            min_score=72,
            daily_invite_limit=15,
            daily_message_limit=30,
            created_at=days_ago(2),
        )
        session.add(draft_campaign)
        await session.flush()
        for index, (action_type, delay, body) in enumerate(
            [
                (
                    "connection_request",
                    0,
                    "Bonjour {{first_name}}, félicitations pour votre nouveau poste chez {{company}}. J'ai vu {{signal}}. {{icebreaker}}",
                ),
                (
                    "message",
                    1,
                    "Merci pour la connexion ! {{icebreaker}}\n\nPartant pour 15 minutes d'échange sur ce sujet ?",
                ),
            ]
        ):
            session.add(
                SequenceStep(
                    campaign_id=draft_campaign.id,
                    position=index,
                    action_type=action_type,
                    delay_days=delay,
                    body_template=body,
                )
            )

        paused_campaign = Campaign(
            organization_id=org.id,
            icp_id=icp.id,
            account_id=account.id,
            name="Expansion UK · test",
            description="Première itération sur le marché britannique. En pause pour réviser le message.",
            status="paused",
            auto_launch=False,
            min_score=75,
            daily_invite_limit=10,
            daily_message_limit=20,
            launched_at=days_ago(12),
            paused_at=days_ago(3),
            created_at=days_ago(14),
        )
        session.add(paused_campaign)
        await session.flush()
        session.add(
            SequenceStep(
                campaign_id=paused_campaign.id,
                position=0,
                action_type="connection_request",
                delay_days=0,
                body_template="Bonjour {{first_name}}, j'ai vu {{signal}}. {{icebreaker}}",
            )
        )

        campaign_lead_states = {
            "Claire Dubois": ("replied", 2, now - timedelta(hours=2)),
            "Hugo Lambert": ("meeting", 2, now - timedelta(hours=20)),
            "Sarah Benali": ("messaged", 1, None),
            "Inès Moreau": ("messaged", 1, None),
            "Maxime Rousseau": ("connected", 1, None),
            "Léa Fontaine": ("invited", 1, None),
            "Thomas Garnier": ("enrolled", 0, None),
        }
        campaign_leads: dict[str, CampaignLead] = {}
        for name, (status, current_step, replied_at) in campaign_lead_states.items():
            lead = leads[name]
            cl = CampaignLead(
                campaign_id=campaign.id,
                lead_id=lead.id,
                status=status,
                current_step=current_step,
                last_action_at=now - timedelta(days=rng.uniform(0.3, 4)),
                replied_at=replied_at,
                next_action_at=None if status in {"replied", "meeting"} else now + timedelta(days=rng.uniform(0.5, 4)),
                created_at=now - timedelta(days=rng.uniform(2, 5)),
            )
            session.add(cl)
            await session.flush()
            campaign_leads[name] = cl
            for step_index in range(min(current_step + 1, len(steps))):
                sent = status != "enrolled" or step_index == 0
                session.add(
                    OutboundAction(
                        organization_id=org.id,
                        campaign_id=campaign.id,
                        campaign_lead_id=cl.id,
                        lead_id=lead.id,
                        account_id=account.id,
                        step_id=steps[step_index].id,
                        action_type=steps[step_index].action_type,
                        status="sent" if sent else "scheduled",
                        scheduled_at=now - timedelta(days=rng.uniform(1, 4)),
                        executed_at=now - timedelta(days=rng.uniform(1, 4)) if sent else None,
                        content="Message de démonstration envoyé depuis le compte de Camille.",
                        attempts=1 if sent else 0,
                    )
                )

        for name, data in CONVERSATIONS.items():
            lead = leads[name]
            convo = Conversation(
                organization_id=org.id,
                lead_id=lead.id,
                account_id=account.id,
                campaign_id=campaign.id,
                status=data["status"],
                unread_count=data["unread"],
                last_message_at=now - timedelta(hours=data["last_hours"]),
                last_message_preview="",
                created_at=now - timedelta(days=5),
            )
            session.add(convo)
            await session.flush()
            for direction, body, hours_ago, ai in data["messages"]:
                sent_at = now - timedelta(hours=hours_ago)
                session.add(
                    Message(
                        conversation_id=convo.id,
                        direction=direction,
                        body=body,
                        sender_name=lead.full_name if direction == "inbound" else "Camille Moreau",
                        sent_at=sent_at,
                        is_read=direction == "outbound" or data["unread"] == 0,
                        ai_generated=ai,
                    )
                )
            convo.last_message_preview = data["messages"][-1][1][:300]
            if data["status"] == "meeting":
                lead.status = "meeting"
            elif name == "Claire Dubois":
                lead.status = "replied"
            # A few additional messages across the period keep the activity chart useful.
            for extra in range(3):
                sent_at = now - timedelta(days=extra * 3 + 1, hours=rng.randint(0, 6))
                session.add(
                    Message(
                        conversation_id=convo.id,
                        direction="inbound" if extra % 2 == 1 else "outbound",
                        body="Échange de suivi (données de démonstration).",
                        sender_name=lead.full_name if extra % 2 == 1 else "Camille Moreau",
                        sent_at=sent_at,
                        is_read=True,
                        ai_generated=False,
                    )
                )

        session.add(
            OrganizationInvite(
                organization_id=org.id,
                email="marie@northwind.demo",
                role="member",
                token_hash="seed-invite-placeholder-marie",
                invited_by_id=user.id,
                expires_at=now + timedelta(days=5),
                created_at=days_ago(4),
            )
        )
        for name, title, target in [
            ("Campagne de démonstration lancée", "Objectif : 14 signaux en 7 jours", "Signaux Q4 · Revenue leaders"),
            ("Score ICP moyen : 78", "Les signaux récents performent le mieux", None),
            ("Boîte unifiée connectée", "Le handover humain fonctionne dès la première réponse", None),
        ]:
            session.add(
                AuditEvent(
                    organization_id=org.id,
                    actor_type="system",
                    action=name,
                    target_type="campaign" if target else None,
                    target_id=str(campaign.id) if target else None,
                    extra_data={"detail": title},
                    created_at=now - timedelta(hours=rng.uniform(1, 40)),
                )
            )

        await session.commit()
        logger.info("Demo workspace seeded: %s / %s", settings.demo_user_email, settings.demo_user_password)


if __name__ == "__main__":
    asyncio.run(seed())
