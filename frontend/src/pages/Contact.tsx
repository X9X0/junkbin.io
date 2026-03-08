import { Link } from 'react-router-dom';
import { Mail, AlertTriangle, Newspaper, Bug, MessageSquare } from 'lucide-react';

export default function Contact() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <div className="p-2 bg-cyber-cyan/20 border border-cyber-cyan/50">
          <Mail className="h-6 w-6 text-cyber-cyan" />
        </div>
        <h1 className="font-display text-2xl font-bold tracking-wider text-white">
          CONTACT
        </h1>
      </div>
      <p className="text-gray-500 text-sm font-mono mb-8">
        // use the right channel and you'll get a faster response
      </p>

      <div className="space-y-4">

        {/* Bug Reports */}
        <section className="card-cyber p-6">
          <div className="flex items-center gap-2 mb-3">
            <Bug className="h-5 w-5 text-cyber-green" />
            <h2 className="font-display text-lg font-bold text-cyber-green tracking-wider">
              BUG REPORTS & FEEDBACK
            </h2>
          </div>
          <p className="text-gray-300 text-sm leading-relaxed mb-4">
            Found a bug, broken feature, or have a suggestion? Send us an email and include steps
            to reproduce, your browser and OS, and a description of what you expected vs. what happened.
          </p>
          <a
            href="mailto:admin@junkbin.io"
            className="inline-flex items-center gap-1.5 text-xs font-mono text-cyber-green border border-cyber-green/40 px-3 py-1.5 hover:bg-cyber-green/10 transition-colors"
          >
            <Mail className="h-3.5 w-3.5" />
            admin@junkbin.io
          </a>
        </section>

        {/* Community */}
        <section className="card-cyber p-6">
          <div className="flex items-center gap-2 mb-3">
            <MessageSquare className="h-5 w-5 text-cyber-cyan" />
            <h2 className="font-display text-lg font-bold text-cyber-cyan tracking-wider">
              COMMUNITY & GENERAL
            </h2>
          </div>
          <p className="text-gray-300 text-sm leading-relaxed mb-4">
            Questions, content disputes, or general conversation — use the community channels.
            If you're a registered user, you can reach moderators through the report system or
            direct messages.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              to="/guidelines"
              className="text-xs font-mono text-cyber-cyan border border-cyber-cyan/40 px-3 py-1.5 hover:bg-cyber-cyan/10 transition-colors"
            >
              COMMUNITY GUIDELINES →
            </Link>
            <a
              href="mailto:admin@junkbin.io"
              className="inline-flex items-center gap-1.5 text-xs font-mono text-gray-400 border border-cyber-light/30 px-3 py-1.5 hover:bg-white/5 transition-colors"
            >
              <Mail className="h-3.5 w-3.5" />
              admin@junkbin.io
            </a>
          </div>
        </section>

        {/* DMCA / Legal */}
        <section className="card-cyber p-6 border-cyber-pink/30">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="h-5 w-5 text-cyber-pink" />
            <h2 className="font-display text-lg font-bold text-cyber-pink tracking-wider">
              DMCA & LEGAL
            </h2>
          </div>
          <p className="text-gray-300 text-sm leading-relaxed mb-3">
            Junkbin.io hosts user-contributed schematics, documentation, and technical content in
            support of the Right to Repair movement. All content is provided for educational and
            repair purposes.
          </p>
          <p className="text-gray-300 text-sm leading-relaxed mb-4">
            If you believe content on this site infringes your copyright, send a DMCA takedown
            notice with the following information: identification of the copyrighted work, location
            of the infringing material, your contact information, and a statement of good faith belief.
          </p>
          <a
            href="mailto:admin@junkbin.io"
            className="inline-flex items-center gap-1.5 text-xs font-mono text-cyber-pink border border-cyber-pink/40 px-3 py-1.5 hover:bg-cyber-pink/10 transition-colors"
          >
            <Mail className="h-3.5 w-3.5" />
            admin@junkbin.io
          </a>
        </section>

        {/* Press & Partnerships */}
        <section className="card-cyber p-6">
          <div className="flex items-center gap-2 mb-3">
            <Newspaper className="h-5 w-5 text-cyber-yellow" />
            <h2 className="font-display text-lg font-bold text-cyber-yellow tracking-wider">
              PRESS & PARTNERSHIPS
            </h2>
          </div>
          <p className="text-gray-300 text-sm leading-relaxed mb-4">
            Media inquiries, partnership proposals, or collaboration opportunities — reach out via
            email. We're always interested in connecting with organizations that share our values
            around repair, sustainability, and open knowledge.
          </p>
          <a
            href="mailto:admin@junkbin.io"
            className="inline-flex items-center gap-1.5 text-xs font-mono text-cyber-yellow border border-cyber-yellow/40 px-3 py-1.5 hover:bg-cyber-yellow/10 transition-colors"
          >
            <Mail className="h-3.5 w-3.5" />
            admin@junkbin.io
          </a>
        </section>

        {/* Appeals */}
        <section className="card-cyber p-6">
          <div className="flex items-center gap-2 mb-3">
            <Mail className="h-5 w-5 text-gray-400" />
            <h2 className="font-display text-lg font-bold text-white tracking-wider">
              MODERATION APPEALS
            </h2>
          </div>
          <p className="text-gray-300 text-sm leading-relaxed mb-4">
            If your account has been actioned and you believe it was in error, you can appeal to{' '}
            <a href="mailto:admin@junkbin.io" className="text-cyber-cyan hover:underline">
              admin@junkbin.io
            </a>
            . Include your username and a description of the situation. See the{' '}
            <Link to="/guidelines" className="text-cyber-cyan hover:underline">
              Community Guidelines
            </Link>{' '}
            for the full enforcement and appeals policy.
          </p>
        </section>

      </div>
    </div>
  );
}
