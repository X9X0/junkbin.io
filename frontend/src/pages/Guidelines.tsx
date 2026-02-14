import { Shield, AlertTriangle, MessageSquare, FileText, Scale, Mail } from 'lucide-react';

export default function Guidelines() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <div className="p-2 bg-cyber-cyan/20 border border-cyber-cyan/50">
          <Shield className="h-6 w-6 text-cyber-cyan" />
        </div>
        <h1 className="font-display text-2xl font-bold tracking-wider text-white">
          COMMUNITY GUIDELINES
        </h1>
      </div>
      <p className="text-gray-500 text-sm font-mono mb-8">
        Standards for contributing to the Junkbin.io community
      </p>

      <div className="space-y-6">
        {/* Mission */}
        <section className="card-cyber p-6">
          <h2 className="font-display text-lg font-bold text-cyber-cyan mb-3 tracking-wider">
            OUR MISSION
          </h2>
          <p className="text-gray-300 text-sm leading-relaxed">
            Junkbin.io is a community-driven database for electronic component documentation,
            supporting the Right to Repair movement. We believe repair information should be
            freely accessible. Every contribution helps someone fix a device instead of
            throwing it away. These guidelines exist to keep the community productive,
            respectful, and focused on that goal.
          </p>
        </section>

        {/* Content Standards */}
        <section className="card-cyber p-6">
          <div className="flex items-center gap-2 mb-3">
            <FileText className="h-5 w-5 text-cyber-green" />
            <h2 className="font-display text-lg font-bold text-cyber-green tracking-wider">
              CONTENT STANDARDS
            </h2>
          </div>
          <ul className="space-y-3 text-sm text-gray-300">
            <li className="flex gap-3">
              <span className="text-cyber-green font-mono flex-shrink-0">01</span>
              <span><strong className="text-white">Accuracy matters.</strong> Double-check part numbers, manufacturer names, and reference designators before submitting. If you're unsure, note it in the description.</span>
            </li>
            <li className="flex gap-3">
              <span className="text-cyber-green font-mono flex-shrink-0">02</span>
              <span><strong className="text-white">Cite your sources.</strong> When uploading schematics or datasheets, indicate where they came from (manufacturer site, community reverse-engineering, etc.).</span>
            </li>
            <li className="flex gap-3">
              <span className="text-cyber-green font-mono flex-shrink-0">03</span>
              <span><strong className="text-white">No duplicates.</strong> Search before submitting a new product or component. If it already exists, add to the existing entry instead.</span>
            </li>
            <li className="flex gap-3">
              <span className="text-cyber-green font-mono flex-shrink-0">04</span>
              <span><strong className="text-white">Quality photos.</strong> When uploading PCB images, use good lighting and focus. Clear images help others identify components.</span>
            </li>
            <li className="flex gap-3">
              <span className="text-cyber-green font-mono flex-shrink-0">05</span>
              <span><strong className="text-white">Stay on topic.</strong> Comments should relate to the product, its components, or repair information. Save off-topic discussions for messages.</span>
            </li>
          </ul>
        </section>

        {/* Communication Standards */}
        <section className="card-cyber p-6">
          <div className="flex items-center gap-2 mb-3">
            <MessageSquare className="h-5 w-5 text-cyber-cyan" />
            <h2 className="font-display text-lg font-bold text-cyber-cyan tracking-wider">
              COMMUNICATION STANDARDS
            </h2>
          </div>
          <ul className="space-y-3 text-sm text-gray-300">
            <li className="flex gap-3">
              <span className="text-cyber-cyan font-mono flex-shrink-0">01</span>
              <span><strong className="text-white">Be respectful.</strong> Disagreements about component identification are normal. Discuss the data, not the person.</span>
            </li>
            <li className="flex gap-3">
              <span className="text-cyber-cyan font-mono flex-shrink-0">02</span>
              <span><strong className="text-white">No harassment.</strong> Targeted, repeated, or unwelcome messages to another user are not tolerated. Use the block feature if needed.</span>
            </li>
            <li className="flex gap-3">
              <span className="text-cyber-cyan font-mono flex-shrink-0">03</span>
              <span><strong className="text-white">No hate speech.</strong> Slurs, discriminatory language, and content promoting hatred against any group are prohibited.</span>
            </li>
            <li className="flex gap-3">
              <span className="text-cyber-cyan font-mono flex-shrink-0">04</span>
              <span><strong className="text-white">No spam.</strong> Don't send unsolicited promotional messages or post repetitive content.</span>
            </li>
          </ul>
        </section>

        {/* Prohibited Content */}
        <section className="card-cyber p-6 border-cyber-pink/30">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="h-5 w-5 text-cyber-pink" />
            <h2 className="font-display text-lg font-bold text-cyber-pink tracking-wider">
              PROHIBITED CONTENT
            </h2>
          </div>
          <p className="text-gray-400 text-sm mb-3">
            The following will result in content removal and may lead to account action:
          </p>
          <ul className="space-y-2 text-sm text-gray-300">
            <li className="flex items-start gap-2">
              <span className="text-cyber-pink mt-0.5">&#x2716;</span>
              <span>Deliberately incorrect technical information</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-cyber-pink mt-0.5">&#x2716;</span>
              <span>Spam, advertising, or promotional content</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-cyber-pink mt-0.5">&#x2716;</span>
              <span>Copyright-infringing material without fair use basis</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-cyber-pink mt-0.5">&#x2716;</span>
              <span>NSFW, violent, or graphic content</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-cyber-pink mt-0.5">&#x2716;</span>
              <span>Harassment, threats, or doxxing</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-cyber-pink mt-0.5">&#x2716;</span>
              <span>Hate speech, slurs, or discriminatory language</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-cyber-pink mt-0.5">&#x2716;</span>
              <span>Impersonation of other users or organizations</span>
            </li>
          </ul>
        </section>

        {/* Enforcement */}
        <section className="card-cyber p-6">
          <div className="flex items-center gap-2 mb-3">
            <Scale className="h-5 w-5 text-cyber-yellow" />
            <h2 className="font-display text-lg font-bold text-cyber-yellow tracking-wider">
              ENFORCEMENT
            </h2>
          </div>
          <p className="text-gray-300 text-sm mb-4 leading-relaxed">
            We use a transparent, graduated enforcement system:
          </p>
          <div className="space-y-4">
            <div className="flex items-start gap-4">
              <div className="min-w-[80px] text-center">
                <span className="inline-block px-3 py-1 bg-cyber-cyan/20 border border-cyber-cyan/50 text-cyber-cyan font-mono text-xs">
                  REPORT
                </span>
              </div>
              <p className="text-sm text-gray-400">
                Any user can report content or messages that violate these guidelines. Reports are reviewed by moderators.
              </p>
            </div>
            <div className="flex items-start gap-4">
              <div className="min-w-[80px] text-center">
                <span className="inline-block px-3 py-1 bg-cyber-yellow/20 border border-cyber-yellow/50 text-cyber-yellow font-mono text-xs">
                  STRIKE
                </span>
              </div>
              <p className="text-sm text-gray-400">
                Valid reports result in a strike on the reported user's account. You'll be notified by email when you receive a strike.
              </p>
            </div>
            <div className="flex items-start gap-4">
              <div className="min-w-[80px] text-center">
                <span className="inline-block px-3 py-1 bg-cyber-yellow/20 border border-cyber-yellow/50 text-cyber-yellow font-mono text-xs">
                  REVIEW
                </span>
              </div>
              <p className="text-sm text-gray-400">
                At 3 strikes, your account is automatically flagged for moderator review. Reviews can result in:
              </p>
            </div>
            <div className="ml-[96px] space-y-2 text-sm">
              <p className="text-gray-400">
                <span className="text-cyber-green font-mono">CLEARED</span> — No action needed, strikes were minor or context-dependent
              </p>
              <p className="text-gray-400">
                <span className="text-cyber-yellow font-mono">WARNING</span> — Formal warning issued, no account restrictions
              </p>
              <p className="text-gray-400">
                <span className="text-cyber-pink font-mono">RESTRICTED</span> — Trusted status revoked, contributions require moderation
              </p>
              <p className="text-gray-400">
                <span className="text-cyber-pink font-mono">SUSPENDED</span> — Account deactivated
              </p>
            </div>
          </div>
        </section>

        {/* Appeals */}
        <section className="card-cyber p-6">
          <div className="flex items-center gap-2 mb-3">
            <Mail className="h-5 w-5 text-gray-400" />
            <h2 className="font-display text-lg font-bold text-white tracking-wider">
              APPEALS
            </h2>
          </div>
          <p className="text-gray-300 text-sm leading-relaxed">
            If you believe a moderation action was made in error, you can appeal by
            emailing <a href="mailto:appeals@junkbin.io" className="text-cyber-cyan hover:underline">appeals@junkbin.io</a> with
            your username and a description of the situation. Appeals are reviewed by a different moderator
            than the one who took the original action. We aim to respond within 48 hours.
          </p>
        </section>

        {/* Last updated */}
        <p className="text-center text-xs text-gray-600 font-mono pt-4">
          Last updated: February 2026
        </p>
      </div>
    </div>
  );
}
