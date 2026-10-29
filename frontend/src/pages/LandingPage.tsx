import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import Lenis from 'lenis';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import '@fontsource/instrument-serif/400-italic.css';
import '@fontsource-variable/jetbrains-mono';

import { ArrowRight, BadgeCheck, BellRing, BriefcaseBusiness, Building2, CalendarDays, ChevronDown, CircleCheck, Coins, Eye, FileText, Globe2, Languages, Menu, MessageCircle, Moon, Network, Radar, ShieldCheck, Sun, TrendingUp, UserPlus, Users, UsersRound, X, Zap } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Logo } from '../assets/brand/Logo';
import { useI18n } from '../lib/i18n';
import { pricingConfig } from '../config/pricing';
import '../landing.css';

type LocaleCopy = (typeof copy)[keyof typeof copy];
const copy = {
    fr: {
        nav: ['Fonctionnement', 'Signaux', 'Sécurité', 'Tarifs', 'FAQ'], login: 'Se connecter', trial: 'Essayer gratuitement',
        heroEyebrow: 'Prospection LinkedIn pilotée par les signaux', hero: 'Le bon message, au bon moment.',
        heroSub: "Kairos détecte les signaux d'achat sur LinkedIn et lance vos séquences de prospection au moment où elles ont le plus de chances de convertir.",
        watch: 'Voir comment ça marche', principles: ['11 types de signaux d’achat', 'Quotas et warmup intégrés', 'Connecteur MCP pour Claude'],
        problemTitle: 'La prospection se disperse trop vite.', problem: ['Dix outils à jongler', 'Des messages génériques', 'Des relances qui tombent dans l’oubli'], problemSub: ['Signaux, CRM et séquences vivent dans des outils séparés.', 'Un profil LinkedIn ne suffit pas à retrouver le contexte utile.', 'Une réponse attend une action humaine immédiate, pas une routine rigide.'],
        howTitle: 'Du signal à la conversation', steps: ['Décrivez votre client idéal', 'Kairos détecte les signaux', 'Personnalisez et envoyez', 'Vous reprenez la main à la réponse'],
        signalsTitle: 'Onze signaux qui donnent un contexte', signals: ['Prise de poste', 'Nouvelle mission cible', 'Interaction avec votre contenu', 'Interaction concurrente', 'Lookalike de l’ICP', 'Levée de fonds', 'Recrutement ciblé', 'Publication clé', 'Participation à un événement', 'Croissance des effectifs', 'Visite du profil'],
        campaignTitle: 'Une séquence pertinente, pas une suite automatique', campaignSub: 'Invitation, message puis relance : chaque étape utilise le contexte vérifié. La validation manuelle reste disponible avant chaque envoi.',
        securityTitle: 'La sécurité du compte au premier plan', securitySub: 'Kairos applique des quotas, un warmup progressif et suspend l’activité en cas de restriction, de défi ou de déconnexion. Cela réduit le risque, sans pouvoir l’éliminer. Les conditions LinkedIn restent applicables.',
        uniboxTitle: 'Une réponse, et la main vous revient', uniboxSub: 'L’intention est classée, modifiable et visible à côté de la conversation.',
        mcpTitle: 'Kairos dans Claude, à votre façon', mcpSub: 'Interrogez vos leads et préparez vos actions depuis Claude grâce au connecteur MCP.',
        pricingTitle: 'Une formule adaptée à votre équipe', sample: 'Prix d’exemple configurables', popular: 'Le plus choisi', choose: 'Choisir cette formule', contact: 'Nous contacter',
        monthlyLabel: 'Mensuel', annualLabel: 'Annuel', faqTitle: 'Questions fréquentes', faqs: [['LinkedIn autorise-t-il l’automatisation ?', 'Non pas de façon générale sans limites. Les conditions LinkedIn s’appliquent et toute automatisation comporte un risque de restriction. Kairos applique des quotas, du warmup et la prise de contrôle humaine, sans promettre un risque nul.'], ['Mes données sont-elles protégées ?', 'Les organisations sont isolées. Les oppositions, l’export, la suppression et l’historique d’audit sont prévus par le produit.'], ['Puis-je valider chaque message ?', 'Oui. Le mode de validation manuelle bloque tout envoi jusqu’à votre approbation.'], ['Puis-je utiliser mon propre modèle d’IA ?', 'Oui, via l’interface compatible OpenAI locale ou le fournisseur Anthropic configuré par l’administrateur.'], ['Comment résilier ?', 'Vous pouvez quitter votre abonnement depuis les paramètres administratifs selon les conditions contractuelles de production.']],
        cta: 'Commencez au bon moment.', footerProduct: 'Produit', footerLegal: 'Légaux', legal: 'Mentions légales', privacy: 'Politique de confidentialité', terms: 'Conditions d’utilisation', footerContact: 'Contact', demo: 'Données fictives — démonstration visuelle uniquement',
    },
    en: { nav: ['How it works', 'Signals', 'Security', 'Pricing', 'FAQ'], login: 'Sign in', trial: 'Start free', heroEyebrow: 'Signal-led LinkedIn prospecting', hero: 'The right message, at the right moment.', heroSub: 'Kairos detects buying signals on LinkedIn and launches your outreach sequences when they are most likely to convert.', watch: 'See how it works', principles: ['11 buying signal types', 'Built-in quotas and warmup', 'MCP connector for Claude'], problemTitle: 'Prospecting gets fragmented too quickly.', problem: ['Juggling ten tools', 'Generic messages', 'Forgotten follow-ups'], problemSub: ['Signals, CRM and sequences live in separate tools.', 'A LinkedIn profile is not enough context on its own.', 'A reply needs human action, not a rigid routine.'], howTitle: 'From signal to conversation', steps: ['Describe your ideal customer', 'Kairos detects signals', 'Personalize and send', 'Take over on reply'], signalsTitle: 'Eleven signals that add context', signals: ['Job change', 'New role in target company', 'Interaction with your content', 'Competitor interaction', 'ICP lookalike', 'Funding round', 'Targeted hiring', 'Key publication', 'Event participation', 'Headcount growth', 'Profile visit'], campaignTitle: 'A relevant sequence, not a rigid automation', campaignSub: 'Invitation, message then follow-up: every step uses verified context. Manual approval remains available before every send.', securityTitle: 'Account safety comes first', securitySub: 'Kairos enforces quotas, progressive warmup and suspends activity for restrictions, challenges or disconnection. This reduces risk without eliminating it. LinkedIn terms still apply.', uniboxTitle: 'A reply brings the conversation back to you', uniboxSub: 'Intent is classified, editable and visible beside the conversation.', mcpTitle: 'Kairos inside Claude, your way', mcpSub: 'Query leads and prepare actions from Claude through the MCP connector.', pricingTitle: 'A plan for your team', monthlyLabel: 'Monthly', annualLabel: 'Annual', sample: 'Example prices — configurable', popular: 'Most popular', choose: 'Choose plan', contact: 'Contact us', faqTitle: 'Frequently asked questions', faqs: [['Does LinkedIn allow automation?', 'Not without constraints. LinkedIn terms apply, and any automation carries account restriction risk. Kairos uses quotas, warmup and human handoff, without promising zero risk.'], ['Is my data protected?', 'Organizations are isolated. Opt-outs, export, deletion and audit history are supported by the product.'], ['Can I approve every message?', 'Yes. Manual validation blocks sending until you approve it.'], ['Can I use my own AI model?', 'Yes, through the OpenAI-compatible interface for a local model or the administrator-configured Anthropic provider.'], ['How do I cancel?', 'You can cancel from administrative settings according to production contract terms.']], cta: 'Start at the right moment.', footerProduct: 'Product', footerLegal: 'Legal', legal: 'Legal notice', privacy: 'Privacy policy', terms: 'Terms of use', footerContact: 'Contact', demo: 'Fictional data — visual demonstration only' }
} as const;

function ThemeToggle() { const [theme, setTheme] = useState<'light' | 'dark'>(() => (localStorage.getItem('kairos-theme') as 'light' | 'dark') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'dark')); useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem('kairos-theme', theme) }, [theme]); return <button className="landing-icon" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} aria-label="Toggle theme">{theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}</button> }

function SignalsSection({ t, locale }: { t: LocaleCopy; locale: 'fr' | 'en' }) {
    const trackRef = useRef<HTMLDivElement>(null);
    const [active, setActive] = useState(0);
    const fr = locale === 'fr';
    const details = fr ? [
        ['Le contexte a changé', 'Un changement de fonction peut ouvrir une nouvelle priorité commerciale.', '« Une nouvelle direction commerciale rejoint l’entreprise »'],
        ['La cible recrute', 'Une arrivée clé confirme qu’une équipe cherche à accélérer.', '« Un VP Sales arrive chez un compte SaaS B2B »'],
        ['Le prospect vous connaît', 'Une réaction à votre contenu révèle une proximité déjà créée.', '« Le décideur commente votre publication sur le cycle de vente »'],
        ['Un sujet commun émerge', 'Une interaction avec un concurrent contextualise l’intérêt actuel.', '« Le prospect suit les publications d’un acteur concurrent »'],
        ['Le profil ressemble à vos gagnants', 'Kairos compare le prospect avec les profils qui convertissent déjà.', '« Même fonction, même taille, même dynamique commerciale »'],
        ['La capacité d’investissement augmente', 'Une levée de fonds peut déclencher une phase de croissance.', '« Une série B est annoncée dans un secteur prioritaire »'],
        ['Le besoin est en recrutement', 'L’embauche sur le poste de vente révèle une priorité opérationnelle.', '« Trois commerciaux sont recherchés dans la même équipe »'],
        ['Le sujet devient prioritaire', 'Une publication rend visible une problématique liée à votre offre.', '« Le dirigeant publie sur l’organisation du pipeline »'],
        ['Le marché se rassemble', 'Une participation à un événement expose un centre d’intérêt actif.', '« Le décideur intervient sur une conférence sectorielle »'],
        ['L’organisation grandit', 'Une hausse des effectifs peut nécessiter de nouveaux outils.', '« L’effectif commercial augmente depuis trois mois »'],
        ['Une attention explicite apparaît', 'Une visite de profil est utilisée seulement si la source le permet.', '« Le prospect consulte votre profil professionnel »'],
    ] : [
        ['The context changed', 'A role change may create a new commercial priority.', '“A new sales leader joins the company”'],
        ['The target is hiring', 'A key arrival confirms that a team is scaling.', '“A VP Sales joins a B2B SaaS account”'],
        ['The prospect already knows you', 'Engagement with your content signals existing relevance.', '“A decision-maker comments on your sales cycle post”'],
        ['A shared topic emerges', 'Competitor engagement helps contextualize current interest.', '“The prospect follows a competing solution’s posts”'],
        ['The profile resembles your winners', 'Kairos compares the prospect with profiles that already convert.', '“Same role, company size and commercial momentum”'],
        ['Investment capacity increases', 'A funding round can trigger a growth phase.', '“A series B is announced in a priority sector”'],
        ['The need is visible in hiring', 'Sales recruiting reveals an operational priority.', '“Three account executives are open in the same team”'],
        ['The topic becomes a priority', 'A public post reveals a challenge linked to your offer.', '“The executive posts about pipeline organization”'],
        ['The market gathers', 'Event participation exposes an active area of interest.', '“The decision-maker speaks at an industry conference”'],
        ['The organization is growing', 'Headcount growth can create demand for new tools.', '“The sales team has grown over the last three months”'],
        ['Explicit attention appears', 'Profile visits are used only when the source provides them.', '“The prospect views your professional profile”'],
    ];
    const icons = [BriefcaseBusiness, UserPlus, MessageCircle, Network, UsersRound, Coins, TrendingUp, FileText, CalendarDays, Building2, Eye];
    const select = (index: number) => {
        setActive(index);
        trackRef.current?.querySelectorAll<HTMLElement>('.signal-card-premium')[index]?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'nearest', inline: 'center' });
    };
    return <section className="section signals-section" id="signals" aria-labelledby="signals-heading">
        <div className="landing-container">
            <div className="signals-header">
                <div className="section-heading"><span>03</span><div><p className="signals-eyebrow">{fr ? 'Contexte commercial' : 'Commercial context'}</p><h2 id="signals-heading">{t.signalsTitle}</h2></div></div>
                <div className="signal-counter" aria-live="polite"><strong>{String(active + 1).padStart(2, '0')}</strong><span>/ 11</span></div>
            </div>
            <div className="signal-stage">
                <motion.aside key={active} className="signal-intro" data-reveal initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .38, ease: [.22, 1, .36, 1] }}>
                    <div className="signal-intro-mark"><Radar size={18} /><span>{String(active + 1).padStart(2, '0')}</span></div>
                    <p className="signal-kicker">{fr ? 'Un contexte vérifiable, pas une supposition.' : 'Verified context, not guesswork.'}</p>
                    <h3>{details[active][0]}</h3>
                    <p>{details[active][1]}</p>
                    <div className="signal-example"><span>{fr ? 'Signal détecté' : 'Detected signal'}</span><p>{details[active][2]}</p></div>
                </motion.aside>
                <div className="signal-track-shell">
                    <div ref={trackRef} className="signal-track" onScroll={(event) => {
                        const cards = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('.signal-card-premium'));
                        const center = event.currentTarget.scrollLeft + event.currentTarget.clientWidth / 2;
                        let nearest = 0, distance = Number.POSITIVE_INFINITY;
                        cards.forEach((card, index) => { const cardCenter = card.offsetLeft + card.clientWidth / 2; const current = Math.abs(cardCenter - center); if (current < distance) { distance = current; nearest = index; } });
                        setActive(nearest);
                    }}>
                        {t.signals.map((signal, i) => { const Icon = icons[i] || Zap; const [heading, explanation] = details[i]; return <motion.article key={signal} role="button" tabIndex={0} className={`signal-card-premium ${active === i ? 'is-active' : ''}`} whileHover={{ y: -6 }} onClick={() => select(i)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); select(i); } }} aria-label={`${i + 1}. ${signal}`} aria-pressed={active === i}><div className="signal-card-top"><span>{String(i + 1).padStart(2, '0')}</span><div className="signal-card-icon"><Icon /></div></div><div className="signal-card-body"><p>{heading}</p><h3>{signal}</h3><span>{explanation}</span></div><div className="signal-card-foot"><Radar size={13} /><span>{fr ? 'Poids configurable' : 'Configurable weight'}</span></div></motion.article>; })}
                    </div>
                    <div className="signal-controls">
                        <button type="button" className="signal-arrow" onClick={() => select(Math.max(0, active - 1))} disabled={active === 0} aria-label={fr ? 'Signal précédent' : 'Previous signal'}>←</button>
                        <div className="signal-dots">{t.signals.map((signal, i) => <button type="button" key={signal} className={active === i ? 'is-active' : ''} onClick={() => select(i)} aria-label={`${fr ? 'Afficher' : 'Show'} ${signal}`} aria-current={active === i ? 'true' : undefined} />)}</div>
                        <button type="button" className="signal-arrow" onClick={() => select(Math.min(10, active + 1))} disabled={active === 10} aria-label={fr ? 'Signal suivant' : 'Next signal'}>→</button>
                    </div>
                </div>
            </div>
        </div>
    </section>;
}

function HeroMockup({ t }: { t: LocaleCopy }) { return <div className="hero-mock" aria-label="Product interface mockup"><div className="mock-top"><span /><span /><span /><b>Kairos</b></div><div className="mock-grid"><aside><div className="mock-logo"><Radar size={15} /></div><i /><i /><i /><i /></aside><main><div className="mock-heading"><span>Prospects prioritaires</span><b>Démo</b></div><div className="signal-card ghost-card" /><div className="signal-card"><div><BellRing size={15} /><span>Levée de fonds détectée</span></div><strong>92</strong></div><div className="profile-row"><div className="avatar">SB</div><div><b>Sarah Benali</b><span>Head of Growth · Kanso</span></div><em>Lead chaud</em></div><div className="message-card"><small>Icebreaker généré</small><p>Sarah, votre point de vue sur l’acquisition B2B apporte un contexte utile à votre croissance chez Kanso.</p><span>300 caractères max.</span></div><div className="reply-pulse"><CircleCheck size={14} /> Réponse détectée — séquence arrêtée</div></main></div><p className="demo-note">{t.demo}</p></div> }

export default function LandingPage() {
    const { locale, setLocale } = useI18n(); const t = copy[locale]; const [mobile, setMobile] = useState(false); const [annual, setAnnual] = useState(true); const [scrolled, setScrolled] = useState(false);
    useEffect(() => {
        gsap.registerPlugin(ScrollTrigger);
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        const lenis = new Lenis({ duration: 1.1, smoothWheel: true, wheelMultiplier: .85 });
        lenis.on('scroll', ScrollTrigger.update);
        gsap.ticker.add((time) => lenis.raf(time * 1000)); gsap.ticker.lagSmoothing(0);
        const progress = document.querySelector<HTMLElement>('.reading-progress-bar');
        const update = () => { setScrolled(window.scrollY > 24); if (progress) progress.style.transform = `scaleX(${Math.min(1, window.scrollY / (document.documentElement.scrollHeight - window.innerHeight))})` };
        window.addEventListener('scroll', update, { passive: true }); update();
        gsap.utils.toArray<HTMLElement>('[data-reveal]').forEach((el) => gsap.fromTo(el, { opacity: 0, y: 28 }, { opacity: 1, y: 0, duration: .85, ease: 'cubic-bezier(0.22,1,0.36,1)', scrollTrigger: { trigger: el, start: 'top 86%', once: true } }));
        return () => { window.removeEventListener('scroll', update); gsap.ticker.remove((time) => lenis.raf(time * 1000)); lenis.destroy(); ScrollTrigger.getAll().forEach(t => t.kill()) };
    }, []);
    useEffect(() => { document.title = locale === 'fr' ? 'Kairos — Le bon message, au bon moment.' : 'Kairos — The right message, at the right moment.'; document.documentElement.lang = locale; const description = locale === 'fr' ? "Kairos détecte les signaux d'achat LinkedIn et lance une prospection B2B au bon moment." : "Kairos detects LinkedIn buying signals and launches B2B outreach at the right moment."; let meta = document.querySelector('meta[name="description"]'); if (meta) meta.setAttribute('content', description); meta = document.querySelector('meta[property="og:description"]'); if (meta) meta.setAttribute('content', description) }, [locale]);
    const nav = [['#how'], ['#signals'], ['#security'], ['#pricing'], ['#faq']] as const;
    return <div className="landing"><div className="reading-progress" aria-hidden="true"><div className="reading-progress-bar" /></div><div className="landing-grain" aria-hidden="true" /><header className={`landing-nav ${scrolled ? 'is-scrolled' : ''}`}><div className="landing-container nav-inner"><Link to="/" aria-label="Kairos"><Logo variant="full" theme="dark" size={32} /></Link><nav aria-label="Navigation principale">{t.nav.map((label, i) => <a href={nav[i][0]} key={label}>{label}</a>)}</nav><div className="nav-actions"><button className="landing-icon" onClick={() => setLocale(locale === 'fr' ? 'en' : 'fr')} aria-label="Change language"><Languages size={17} /><span>{locale.toUpperCase()} </span></button><ThemeToggle /><Link className="nav-login" to="/login">{t.login}</Link><Link className="landing-button amber small" to="/login">{t.trial}</Link><button className="mobile-menu landing-icon" onClick={() => setMobile(!mobile)} aria-label="Menu">{mobile ? <X /> : <Menu />}</button></div></div>{mobile && <nav className="mobile-nav">{t.nav.map((label, i) => <a key={label} onClick={() => setMobile(false)} href={nav[i][0]}>{label}</a>)}<Link to="/login">{t.login}</Link></nav>}</header>
        <main><section className="hero landing-container"><motion.div className="hero-copy" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .5 }}><div className="eyebrow"><Radar size={14} />{t.heroEyebrow}</div><h1><span>{locale === 'fr' ? 'Le bon message, au' : 'The right message, at'}</span><em>{locale === 'fr' ? 'bon moment.' : 'the right moment.'}</em></h1><p>{t.heroSub}</p><div className="hero-actions"><Link className="landing-button amber" to="/login">{t.trial}<ArrowRight size={17} /></Link><a className="landing-button ghost" href="#how">{t.watch}</a></div></motion.div><motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: .65 }}><HeroMockup t={t} /></motion.div></section>
            <div className="signal-marquee" aria-label="Signaux d’achat">
                <div className="signal-marquee-track">{[...t.signals, ...t.signals].map((signal, i) => <span key={`${signal}-${i}`}><Radar size={14} />{signal}</span>)}</div>
            </div>
            <section className="principles"><div className="landing-container principle-grid">{t.principles.map((item, i) => <div key={item}>{i === 0 ? <Radar /> : i === 1 ? <ShieldCheck /> : <Network />}<span>{item}</span></div>)}</div></section>
            <section className="section landing-container" id="problem"><div className="section-heading"><span>01</span><h2>{t.problemTitle}</h2></div><div className="three-grid">{t.problem.map((item, i) => <article className="glass-card" key={item}><div className="card-icon">{i === 0 ? <Network /> : i === 1 ? <MessageCircle /> : <BellRing />}</div><h3>{item}</h3><p>{t.problemSub[i]}</p></article>)}</div></section>
            <section className="section landing-container" id="how"><div className="section-heading"><span>02</span><h2>{t.howTitle}</h2></div><div className="steps">{t.steps.map((step, i) => <motion.article initial={{ opacity: 0, y: 18 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * .08 }} key={step}><b>0{i + 1}</b><div className="step-icon">{i === 0 ? <Users /> : i === 1 ? <Radar /> : i === 2 ? <MessageCircle /> : <CircleCheck />}</div><h3>{step}</h3></motion.article>)}</div></section>
            <SignalsSection t={t} locale={locale} />
            <section className="section landing-container split-section" id="campaigns"><div><div className="section-heading compact"><span>04</span><h2>{t.campaignTitle}</h2></div><p className="section-copy">{t.campaignSub}</p><div className="check-list"><span><BadgeCheck />Invitation</span><span><BadgeCheck />Message</span><span><BadgeCheck />Relance</span></div></div><div className="sequence-mock"><div className="sequence-line" /><div className="sequence-step"><b>1</b><div><span>Invitation</span><p>Bonjour Sarah, votre travail chez Kanso sur l’acquisition B2B a retenu notre attention.</p></div></div><div className="sequence-step"><b>2</b><div><span>Message</span><p>Merci pour la connexion — le contexte de vos priorités est utile.</p></div></div><div className="sequence-step muted"><b>3</b><div><span>Relance</span><p>Prévue dans 3 jours seulement si aucune réponse.</p></div></div></div></section>
            <section className="section landing-container" id="bento">
                <div className="section-heading"><span>04+</span><h2>{locale === 'fr' ? 'Chaque détail, au bon endroit.' : 'Every detail, in the right place.'}</h2></div>
                <div className="bento-grid" data-reveal>
                    <article className="bento-card bento-score"><div><Radar /><span>Scoring ICP</span></div><strong>92<span>/100</span></strong><div className="mini-score"><i /></div><p>Signal récent · financement détecté</p></article>
                    <article className="bento-card bento-sequence"><div><MessageCircle /><span>Séquence</span></div><ol><li><b>Invitation</b><em>Envoyée</em></li><li><b>Message</b><em>Prévu</em></li><li><b>Relance</b><em>J+3</em></li></ol></article>
                    <article className="bento-card bento-warmup"><div><ShieldCheck /><span>Warmup</span></div><div className="gauge"><i /><b>64%</b></div><p>Rythme prudent · semaine 4</p></article>
                    <article className="bento-card bento-team"><div><Users /><span>Coordination</span></div><div className="seat-row"><span>AM</span><i /><span>JL</span></div><p>Historique partagé · aucune collision</p></article>
                    <article className="bento-card bento-unibox"><div><BadgeCheck /><span>Unibox</span></div><blockquote>« Votre approche au bon moment me semble pertinente. »</blockquote><b className="intent-chip">Intéressé</b></article>
                </div>
            </section>
            <section className="section landing-container split-section" id="security"><div><div className="section-heading compact"><span>05</span><h2>{t.securityTitle}</h2></div><p className="section-copy">{t.securitySub}</p></div><div className="security-grid"><div><ShieldCheck /><b>Quotas</b><span>Atomes en base avant envoi</span></div><div><Zap /><b>Warmup</b><span>Prudent · normal · rapide</span></div><div><Globe2 /><b>RGPD</b><span>Opposition et effacement</span></div></div></section>
            <section className="section landing-container split-section" id="unibox"><div className="unibox-mock"><div className="inbox-list"><b>Conversations</b><div className="active"><span>SB</span><p><b>Sarah Benali</b><small>Le sujet m’intéresse</small></p><em>2m</em></div><div><span>HL</span><p><b>Hugo Lambert</b><small>Plus tard</small></p></div></div><div className="chat"><b>Sarah Benali</b><div className="bubble">Bonjour, votre approche au bon moment me semble pertinente.</div><div className="intent"><BadgeCheck /> Intéressé</div></div></div><div><div className="section-heading compact"><span>06</span><h2>{t.uniboxTitle}</h2></div><p className="section-copy">{t.uniboxSub}</p></div></section>
            <section className="section landing-container" id="mcp"><div className="mcp-block"><div><div className="section-heading compact light"><span>07</span><h2>{t.mcpTitle}</h2></div><p>{t.mcpSub}</p><code>{`{
  "mcpServers": { "kairos": { "url": "https://votre-domaine/mcp" } }
}`}</code></div><div className="chat-example"><div className="user-message">Montre-moi les leads chauds de la semaine</div><div className="claude-message"><span>Claude</span><p>J’ai identifié 8 prospects dont le score est supérieur à 70. Voulez-vous les afficher avec leur dernier signal ?</p></div></div></div></section>
            <section className="section landing-container" id="pricing"><div className="section-heading centered"><span>08</span><h2>{t.pricingTitle}</h2></div><div className="billing"><button className={!annual ? 'active' : ''} onClick={() => setAnnual(false)}>{t.monthlyLabel}</button><button className={annual ? 'active' : ''} onClick={() => setAnnual(true)}>{t.annualLabel}</button></div><p className="sample-note">{t.sample}</p><div className="pricing-grid">{pricingConfig.plans.map((plan) => { const featured = 'featured' in plan && plan.featured; return <article className={featured ? 'price-card featured' : 'price-card'} key={plan.name.en}>{featured && <span className="popular">{t.popular}</span>}<h3>{plan.name[locale]}</h3><p>{plan.description[locale]}</p><div className="price">{plan.monthly === null ? <strong>{t.contact}</strong> : <><strong>€{annual ? plan.annual : plan.monthly}</strong><span>/ mois</span></>}</div><ul>{plan.features.map(f => <li key={f.en}><CircleCheck />{f[locale]}</li>)}</ul><Link className={featured ? 'landing-button amber' : 'landing-button ghost'} to="/login">{plan.monthly === null ? t.contact : t.choose}</Link></article> })}</div></section>
            <section className="section landing-container" id="faq"><div className="section-heading centered"><span>09</span><h2>{t.faqTitle}</h2></div><div className="faq-list">{t.faqs.map(([q, a]) => <details key={q}><summary>{q}<ChevronDown /></summary><p>{a}</p></details>)}</div></section>
            <section className="final-cta landing-container"><div><span>KAÏROS · {locale === 'fr' ? 'LE MOMENT OPORTUN' : 'THE RIGHT MOMENT'}</span><h2>{t.cta}</h2></div><Link className="landing-button amber" to="/login">{t.trial}<ArrowRight /></Link></section></main>
        <footer><div className="landing-container footer-grid"><div><Logo variant="full" theme="dark" size={34} /><p>Le bon message, au bon moment.</p></div><div><b>{t.footerProduct}</b><a href="#how">{t.nav[0]}</a><a href="#signals">{t.nav[1]}</a><a href="#pricing">{t.nav[3]}</a></div><div><b>{t.footerLegal}</b><Link to="/mentions-legales">{t.legal}</Link><Link to="/privacy">{t.privacy}</Link><Link to="/terms">{t.terms}</Link></div><div><b>{t.footerContact}</b><a href="mailto:hello@kairos.app">hello@kairos.app</a></div></div></footer></div>
}
