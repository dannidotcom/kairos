export const pricingConfig = {
  monthlyLabel: { fr: 'Mensuel', en: 'Monthly' },
  annualLabel: { fr: 'Annuel', en: 'Annual' },
  samplePrices: true,
  plans: [
    { name: { fr: 'Solo', en: 'Solo' }, monthly: 49, annual: 39, description: { fr: 'Pour un fondateur ou commercial indépendant.', en: 'For an independent founder or salesperson.' }, features: [{ fr: '1 compte LinkedIn', en: '1 LinkedIn account' }, { fr: '1 000 prospects suivis', en: '1,000 tracked prospects' }, { fr: 'Signaux et scoring ICP', en: 'Signals and ICP scoring' }, { fr: 'Validation manuelle', en: 'Manual validation' }] },
    { name: { fr: 'Équipe', en: 'Team' }, monthly: 129, annual: 99, featured: true, description: { fr: 'Pour des équipes commerciales collaboratives.', en: 'For collaborative sales teams.' }, features: [{ fr: 'Jusqu’à 5 comptes LinkedIn', en: 'Up to 5 LinkedIn accounts' }, { fr: 'Historique partagé', en: 'Shared history' }, { fr: 'Automatisation et Unibox', en: 'Automation and Unibox' }, { fr: 'Serveur MCP', en: 'MCP server' }] },
    { name: { fr: 'Entreprise', en: 'Enterprise' }, monthly: null, annual: null, description: { fr: 'Pour les organisations aux besoins avancés.', en: 'For organizations with advanced needs.' }, features: [{ fr: 'Volume adapté', en: 'Tailored volume' }, { fr: 'Sécurité renforcée', en: 'Enhanced security' }, { fr: 'Intégration dédiée', en: 'Dedicated integration' }, { fr: 'Support prioritaire', en: 'Priority support' }] },
  ],
} as const;
