export type Locale = 'fr' | 'en';
export type ID = string;

export interface User { id: ID; email: string; full_name: string; locale: Locale; avatar_url?: string | null; last_login_at?: string | null; created_at: string }
export interface Organization { id: ID; name: string; slug: string; plan: string; locale: Locale; timezone: string; is_demo: boolean; daily_invite_limit: number; daily_message_limit: number; warmup_enabled: boolean; logo_url?: string | null; data_retention_days?: number; created_at?: string }
export interface Membership { id: ID; role: 'owner' | 'admin' | 'member'; title?: string | null; is_active: boolean; organization: Organization }
export interface AuthResponse { access_token: string; refresh_token: string; token_type: string; expires_in: number; user: User; organizations: Membership[] }
export interface MeResponse { user: User; organizations: Membership[]; active_organization_id: ID }

export interface Signal { id: ID; type: string; title: string; description?: string | null; source_url?: string | null; source: string; strength: number; status: string; detected_at: string; lead?: LeadBrief | null }
export interface LeadBrief { id: ID; full_name: string; first_name: string; last_name: string; headline?: string | null; company?: string | null; company_size?: string | null; industry?: string | null; location?: string | null; avatar_url?: string | null; linkedin_url: string; status: string; icp_score: number }
export interface Lead extends LeadBrief { email?: string | null; owner_user_id?: ID | null; source: string; tags: string[]; score_reasons: ScoreReason[]; last_signal_at?: string | null; last_contacted_at?: string | null; last_replied_at?: string | null; created_at: string; campaign_names: string[]; unread_count: number; conversation_id?: ID | null; latest_signal?: Signal | null; about?: string | null; phone?: string | null; linkedin_urn?: string | null; extra_data?: Record<string, unknown>; signals?: Signal[]; conversations?: Array<Record<string, unknown>> }
export interface ScoreReason { label?: string; reason?: string; detail?: string; points?: number; score?: number; matched?: boolean; [key: string]: unknown }
export interface LeadListResponse { items: Lead[]; total: number; page: number; page_size: number }
export interface SignalListResponse { items: Signal[]; total: number; page: number; page_size: number }

export interface ICP { id: ID; name: string; description: string; value_prop?: string | null; keywords: string[]; titles: string[]; industries: string[]; company_sizes: string[]; locations: string[]; seniorities: string[]; pain_points: string[]; signal_types: string[]; min_score: number; auto_launch: boolean; is_active: boolean; generated_by: string; created_at: string; updated_at: string }
export type ICPSuggestion = Omit<ICP, 'id' | 'created_at' | 'updated_at' | 'is_active' | 'generated_by'> & { generated_by: string };

export interface SequenceStep { id?: ID; position?: number; action_type: 'connection_request' | 'message' | 'follow_up' | 'inmail'; delay_days: number; body_template: string; is_active: boolean }
export interface CampaignStats { total_leads: number; contacted: number; replied: number; meetings: number; reply_rate: number }
export interface Campaign { id: ID; name: string; description?: string | null; icp_id: ID; account_id?: ID | null; auto_launch: boolean; min_score: number; daily_invite_limit: number; daily_message_limit: number; status: string; launched_at?: string | null; paused_at?: string | null; completed_at?: string | null; created_at: string; updated_at: string; steps: SequenceStep[]; icp_name?: string | null; account_name?: string | null; stats: CampaignStats }
export interface CampaignLead { id: ID; status: string; current_step: number; next_action_at?: string | null; last_action_at?: string | null; replied_at?: string | null; lead: LeadBrief }
export interface CampaignDetail extends Campaign { leads: CampaignLead[] }
export interface CampaignListResponse { items: Campaign[]; total: number }

export interface Message { id: ID; direction: 'inbound' | 'outbound'; body: string; sender_name?: string | null; sent_at: string; is_read: boolean; ai_generated: boolean }
export interface Conversation { id: ID; status: string; unread_count: number; last_message_at: string; last_message_preview?: string | null; is_archived: boolean; lead: LeadBrief; campaign_name?: string | null; last_message?: Message | null }
export interface ConversationDetail extends Conversation { messages: Message[] }
export interface ConversationListResponse { items: Conversation[]; total: number }

export interface LinkedInAccount { id: ID; display_name: string; account_urn?: string | null; provider: string; status: string; avatar_url?: string | null; daily_invite_limit: number; daily_message_limit: number; invites_sent_today: number; messages_sent_today: number; warmup_started_at?: string | null; last_sync_at?: string | null; connected_at?: string | null; last_error?: string | null }
export interface Usage { invites_used: number; invites_limit: number; messages_used: number; messages_limit: number; warmup_active: boolean }

export interface ActivityPoint { date: string; signals: number; messages: number; replies: number }
export interface Dashboard { total_leads: number; hot_leads: number; signals_7d: number; signals_today: number; active_campaigns: number; replies_7d: number; meetings: number; reply_rate: number; avg_icp_score: number; funnel: Array<{ status: string; count: number }>; activity: ActivityPoint[]; recent_signals: Signal[]; recent_conversations: Conversation[]; campaigns: Array<{ id: ID; name: string; status: string; leads: number; contacted: number; replied: number; reply_rate: number }>; usage?: Usage | null }
export interface Member { membership_id: ID; user_id: ID; email: string; full_name: string; avatar_url?: string | null; role: string; title?: string | null; is_active: boolean; last_login_at?: string | null; created_at: string }
export interface ApiKey { id: ID; name: string; key_prefix: string; last_used_at?: string | null; revoked_at?: string | null; created_at: string; key?: string }
export interface AuditEvent { id: ID; actor_type: string; action: string; target_type?: string | null; target_id?: string | null; extra_data: Record<string, unknown>; created_at: string }
