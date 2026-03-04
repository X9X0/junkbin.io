import { useTranslation } from 'react-i18next';
import { Shield, AlertTriangle, MessageSquare, FileText, Scale, Mail } from 'lucide-react';

export default function Guidelines() {
  const { t } = useTranslation();

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <div className="p-2 bg-cyber-cyan/20 border border-cyber-cyan/50">
          <Shield className="h-6 w-6 text-cyber-cyan" />
        </div>
        <h1 className="font-display text-2xl font-bold tracking-wider text-white">
          {t('guidelines.title')}
        </h1>
      </div>
      <p className="text-gray-500 text-sm font-mono mb-8">
        {t('guidelines.subtitle')}
      </p>

      <div className="space-y-6">
        {/* Mission */}
        <section className="card-cyber p-6">
          <h2 className="font-display text-lg font-bold text-cyber-cyan mb-3 tracking-wider">
            {t('guidelines.section_mission')}
          </h2>
          <p className="text-gray-300 text-sm leading-relaxed">
            {t('guidelines.mission_text')}
          </p>
        </section>

        {/* Content Standards */}
        <section className="card-cyber p-6">
          <div className="flex items-center gap-2 mb-3">
            <FileText className="h-5 w-5 text-cyber-green" />
            <h2 className="font-display text-lg font-bold text-cyber-green tracking-wider">
              {t('guidelines.section_content')}
            </h2>
          </div>
          <ul className="space-y-3 text-sm text-gray-300">
            <li className="flex gap-3">
              <span className="text-cyber-green font-mono flex-shrink-0">01</span>
              <span><strong className="text-white">{t('guidelines.content_01_title')}</strong> {t('guidelines.content_01_text')}</span>
            </li>
            <li className="flex gap-3">
              <span className="text-cyber-green font-mono flex-shrink-0">02</span>
              <span><strong className="text-white">{t('guidelines.content_02_title')}</strong> {t('guidelines.content_02_text')}</span>
            </li>
            <li className="flex gap-3">
              <span className="text-cyber-green font-mono flex-shrink-0">03</span>
              <span><strong className="text-white">{t('guidelines.content_03_title')}</strong> {t('guidelines.content_03_text')}</span>
            </li>
            <li className="flex gap-3">
              <span className="text-cyber-green font-mono flex-shrink-0">04</span>
              <span><strong className="text-white">{t('guidelines.content_04_title')}</strong> {t('guidelines.content_04_text')}</span>
            </li>
            <li className="flex gap-3">
              <span className="text-cyber-green font-mono flex-shrink-0">05</span>
              <span><strong className="text-white">{t('guidelines.content_05_title')}</strong> {t('guidelines.content_05_text')}</span>
            </li>
          </ul>
        </section>

        {/* Communication Standards */}
        <section className="card-cyber p-6">
          <div className="flex items-center gap-2 mb-3">
            <MessageSquare className="h-5 w-5 text-cyber-cyan" />
            <h2 className="font-display text-lg font-bold text-cyber-cyan tracking-wider">
              {t('guidelines.section_communication')}
            </h2>
          </div>
          <ul className="space-y-3 text-sm text-gray-300">
            <li className="flex gap-3">
              <span className="text-cyber-cyan font-mono flex-shrink-0">01</span>
              <span><strong className="text-white">{t('guidelines.comm_01_title')}</strong> {t('guidelines.comm_01_text')}</span>
            </li>
            <li className="flex gap-3">
              <span className="text-cyber-cyan font-mono flex-shrink-0">02</span>
              <span><strong className="text-white">{t('guidelines.comm_02_title')}</strong> {t('guidelines.comm_02_text')}</span>
            </li>
            <li className="flex gap-3">
              <span className="text-cyber-cyan font-mono flex-shrink-0">03</span>
              <span><strong className="text-white">{t('guidelines.comm_03_title')}</strong> {t('guidelines.comm_03_text')}</span>
            </li>
            <li className="flex gap-3">
              <span className="text-cyber-cyan font-mono flex-shrink-0">04</span>
              <span><strong className="text-white">{t('guidelines.comm_04_title')}</strong> {t('guidelines.comm_04_text')}</span>
            </li>
          </ul>
        </section>

        {/* Prohibited Content */}
        <section className="card-cyber p-6 border-cyber-pink/30">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="h-5 w-5 text-cyber-pink" />
            <h2 className="font-display text-lg font-bold text-cyber-pink tracking-wider">
              {t('guidelines.section_prohibited')}
            </h2>
          </div>
          <p className="text-gray-400 text-sm mb-3">
            {t('guidelines.prohibited_intro')}
          </p>
          <ul className="space-y-2 text-sm text-gray-300">
            <li className="flex items-start gap-2">
              <span className="text-cyber-pink mt-0.5">&#x2716;</span>
              <span>{t('guidelines.prohibited_01')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-cyber-pink mt-0.5">&#x2716;</span>
              <span>{t('guidelines.prohibited_02')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-cyber-pink mt-0.5">&#x2716;</span>
              <span>{t('guidelines.prohibited_03')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-cyber-pink mt-0.5">&#x2716;</span>
              <span>{t('guidelines.prohibited_04')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-cyber-pink mt-0.5">&#x2716;</span>
              <span>{t('guidelines.prohibited_05')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-cyber-pink mt-0.5">&#x2716;</span>
              <span>{t('guidelines.prohibited_06')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-cyber-pink mt-0.5">&#x2716;</span>
              <span>{t('guidelines.prohibited_07')}</span>
            </li>
          </ul>
        </section>

        {/* Enforcement */}
        <section className="card-cyber p-6">
          <div className="flex items-center gap-2 mb-3">
            <Scale className="h-5 w-5 text-cyber-yellow" />
            <h2 className="font-display text-lg font-bold text-cyber-yellow tracking-wider">
              {t('guidelines.section_enforcement')}
            </h2>
          </div>
          <p className="text-gray-300 text-sm mb-4 leading-relaxed">
            {t('guidelines.enforcement_intro')}
          </p>
          <div className="space-y-4">
            <div className="flex items-start gap-4">
              <div className="min-w-[80px] text-center">
                <span className="inline-block px-3 py-1 bg-cyber-cyan/20 border border-cyber-cyan/50 text-cyber-cyan font-mono text-xs">
                  {t('guidelines.enforcement_report_label')}
                </span>
              </div>
              <p className="text-sm text-gray-400">
                {t('guidelines.enforcement_report_text')}
              </p>
            </div>
            <div className="flex items-start gap-4">
              <div className="min-w-[80px] text-center">
                <span className="inline-block px-3 py-1 bg-cyber-yellow/20 border border-cyber-yellow/50 text-cyber-yellow font-mono text-xs">
                  {t('guidelines.enforcement_strike_label')}
                </span>
              </div>
              <p className="text-sm text-gray-400">
                {t('guidelines.enforcement_strike_text')}
              </p>
            </div>
            <div className="flex items-start gap-4">
              <div className="min-w-[80px] text-center">
                <span className="inline-block px-3 py-1 bg-cyber-yellow/20 border border-cyber-yellow/50 text-cyber-yellow font-mono text-xs">
                  {t('guidelines.enforcement_review_label')}
                </span>
              </div>
              <p className="text-sm text-gray-400">
                {t('guidelines.enforcement_review_text')}
              </p>
            </div>
            <div className="ml-[96px] space-y-2 text-sm">
              <p className="text-gray-400">
                <span className="text-cyber-green font-mono">{t('guidelines.outcome_cleared')}</span> — {t('guidelines.outcome_cleared_text')}
              </p>
              <p className="text-gray-400">
                <span className="text-cyber-yellow font-mono">{t('guidelines.outcome_warning')}</span> — {t('guidelines.outcome_warning_text')}
              </p>
              <p className="text-gray-400">
                <span className="text-cyber-pink font-mono">{t('guidelines.outcome_restricted')}</span> — {t('guidelines.outcome_restricted_text')}
              </p>
              <p className="text-gray-400">
                <span className="text-cyber-pink font-mono">{t('guidelines.outcome_suspended')}</span> — {t('guidelines.outcome_suspended_text')}
              </p>
            </div>
          </div>
        </section>

        {/* Appeals */}
        <section className="card-cyber p-6">
          <div className="flex items-center gap-2 mb-3">
            <Mail className="h-5 w-5 text-gray-400" />
            <h2 className="font-display text-lg font-bold text-white tracking-wider">
              {t('guidelines.section_appeals')}
            </h2>
          </div>
          <p className="text-gray-300 text-sm leading-relaxed">
            {t('guidelines.appeals_text_before')}{' '}
            <a href="mailto:appeals@junkbin.io" className="text-cyber-cyan hover:underline">{t('guidelines.appeals_email')}</a>{' '}
            {t('guidelines.appeals_text_after')}
          </p>
        </section>

        {/* Last updated */}
        <p className="text-center text-xs text-gray-600 font-mono pt-4">
          {t('guidelines.last_updated')}
        </p>
      </div>
    </div>
  );
}
