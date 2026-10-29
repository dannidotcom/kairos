import { Link } from 'react-router-dom';
import { Logo } from '../assets/brand/Logo';
import '../landing.css';

export default function LegalPage({type}:{type:'legal'|'privacy'|'terms'}) {
 const content={
  legal:{title:'Mentions légales',intro:'Document de départ à faire relire par un juriste avant toute mise en production.',sections:[['Éditeur','Kairos — société à compléter, adresse, SIRET et responsable de publication.'],['Hébergement','Informations sur l’hébergeur, ses coordonnées et le pays d’hébergement à compléter.']]},
  privacy:{title:'Politique de confidentialité',intro:'Document générique provisoire. Il doit être adapté au responsable de traitement réel avant production.',sections:[['Données collectées','Compte, organisation, prospects, signaux, conversations, événements d’audit et préférences techniques.'],['Finalités','Prospection B2B, sécurisation du service, support, facturation et conformité.'],['Vos droits','Accès, rectification, opposition, limitation, suppression et portabilité selon le cadre applicable.'],['Conservation','Les durées de conservation et les sous-traitants doivent être documentés avant lancement.']]},
  terms:{title:'Conditions d’utilisation',intro:'Conditions de départ, sans valeur contractuelle définitive sans revue juridique.',sections:[['Compte','Vous êtes responsable des autorisations accordées et des accès de votre organisation.'],['LinkedIn','Vous devez respecter les conditions LinkedIn. L’utilisation comporte un risque de limitation ou restriction du compte. Kairos réduit ce risque mais ne peut l’éliminer.'],['Acceptable Use','Toute usurpation, envoi trompeur, spam, usage contraire aux lois ou contournement des oppositions est interdit.']]}
 }[type];
 return <main className="legal-page"><header><Link to="/"><Logo variant="full" theme="light" size={34}/></Link><Link to="/">Retour à Kairos</Link></header><article><h1>{content.title}</h1><p className="legal-warning">{content.intro}</p>{content.sections.map(([title,body])=><section key={title}><h2>{title}</h2><p>{body}</p></section>)}</article></main>
}
