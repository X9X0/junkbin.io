import { Link } from 'react-router-dom';
import { Wrench, Heart, Globe, Shield, Database, Users, Cpu } from 'lucide-react';

const WEBLATE_PROJECT = 'https://translate.junkbin.io/projects/junkbin-io';

export default function About() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <div className="p-2 bg-cyber-cyan/20 border border-cyber-cyan/50">
          <Wrench className="h-6 w-6 text-cyber-cyan" />
        </div>
        <h1 className="font-display text-2xl font-bold tracking-wider text-white">
          ABOUT <span className="text-cyber-cyan">JUNKBIN</span>
        </h1>
      </div>
      <p className="text-gray-500 text-sm font-mono mb-8">
        // they said "no user serviceable parts inside" — we took that personally
      </p>

      <div className="space-y-6">

        {/* Mission */}
        <section className="card-cyber p-6">
          <h2 className="font-display text-lg font-bold text-cyber-cyan mb-3 tracking-wider">
            THE MISSION
          </h2>
          <p className="text-gray-300 text-sm leading-relaxed mb-3">
            Junkbin.io is a community-driven database documenting the components inside consumer
            electronics — transforming e-waste into a searchable parts catalog for repair, salvage,
            and re-use. Think Wikipedia meets Octopart for teardown documentation.
          </p>
          <p className="text-gray-300 text-sm leading-relaxed">
            Every router, phone, TV, and IoT device that ends up in a landfill is full of perfectly
            usable components. We document them so they can be found, harvested, and put back to
            work — instead of buried.
          </p>
        </section>

        {/* What we do */}
        <section className="card-cyber p-6">
          <h2 className="font-display text-lg font-bold text-cyber-green mb-4 tracking-wider">
            WHAT WE DO
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="flex items-start gap-3">
              <div className="p-1.5 bg-cyber-cyan/10 border border-cyber-cyan/30 flex-shrink-0">
                <Database className="h-4 w-4 text-cyber-cyan" />
              </div>
              <div>
                <h3 className="text-white text-sm font-semibold mb-1">Document Components</h3>
                <p className="text-gray-400 text-xs leading-relaxed">
                  Users tear down electronics and log their bills of materials — ICs, regulators,
                  connectors, and everything in between.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="p-1.5 bg-cyber-green/10 border border-cyber-green/30 flex-shrink-0">
                <Cpu className="h-4 w-4 text-cyber-green" />
              </div>
              <div>
                <h3 className="text-white text-sm font-semibold mb-1">Cross-Reference Parts</h3>
                <p className="text-gray-400 text-xs leading-relaxed">
                  Search by component to find every product that contains it. Need an LM7805?
                  Find out which devices in your junk pile have one.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="p-1.5 bg-cyber-yellow/10 border border-cyber-yellow/30 flex-shrink-0">
                <Users className="h-4 w-4 text-cyber-yellow" />
              </div>
              <div>
                <h3 className="text-white text-sm font-semibold mb-1">Trade & Share Parts</h3>
                <p className="text-gray-400 text-xs leading-relaxed">
                  The Swap Shop connects people who have parts with people who need them.
                  No middleman, no fees — just repair communities helping each other.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="p-1.5 bg-cyber-pink/10 border border-cyber-pink/30 flex-shrink-0">
                <Shield className="h-4 w-4 text-cyber-pink" />
              </div>
              <div>
                <h3 className="text-white text-sm font-semibold mb-1">Share Schematics</h3>
                <p className="text-gray-400 text-xs leading-relaxed">
                  Upload and access service manuals, schematics, and PCB layouts that manufacturers
                  would rather you didn't have.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Right to Repair */}
        <section className="card-cyber p-6 border-cyber-pink/30">
          <h2 className="font-display text-lg font-bold text-cyber-pink mb-3 tracking-wider">
            RIGHT TO REPAIR
          </h2>
          <p className="text-gray-300 text-sm leading-relaxed mb-3">
            We believe you have the right to repair the things you own. Manufacturers use proprietary
            parts, withheld schematics, and software locks to force consumers into expensive replacements
            rather than simple fixes. That's wasteful, expensive, and wrong.
          </p>
          <p className="text-gray-300 text-sm leading-relaxed">
            Junkbin.io exists to push back — by making repair knowledge open, accessible, and free.
            Every schematic uploaded, every component documented, and every part traded here is a
            small act of resistance against planned obsolescence.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <a
              href="https://repair.org"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-mono text-cyber-pink border border-cyber-pink/40 px-3 py-1.5 hover:bg-cyber-pink/10 transition-colors"
            >
              Repair.org →
            </a>
            <a
              href="https://www.ifixit.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-mono text-cyber-pink border border-cyber-pink/40 px-3 py-1.5 hover:bg-cyber-pink/10 transition-colors"
            >
              iFixit →
            </a>
          </div>
        </section>

        {/* Get Involved */}
        <section className="card-cyber p-6">
          <div className="flex items-center gap-2 mb-3">
            <Heart className="h-5 w-5 text-cyber-pink" />
            <h2 className="font-display text-lg font-bold text-white tracking-wider">
              GET INVOLVED
            </h2>
          </div>
          <p className="text-gray-300 text-sm leading-relaxed mb-4">
            Junkbin is built entirely by volunteers who care about repair. There's no VC funding,
            no advertising, no data selling. Just people who think the right to repair matters.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              to="/register"
              className="text-xs font-mono text-cyber-cyan border border-cyber-cyan/40 px-3 py-1.5 hover:bg-cyber-cyan/10 transition-colors"
            >
              CREATE ACCOUNT →
            </Link>
            <Link
              to="/submit"
              className="text-xs font-mono text-cyber-green border border-cyber-green/40 px-3 py-1.5 hover:bg-cyber-green/10 transition-colors"
            >
              CONTRIBUTE DATA →
            </Link>
            <a
              href={WEBLATE_PROJECT}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-xs font-mono text-cyber-green border border-cyber-green/40 px-3 py-1.5 hover:bg-cyber-green/10 transition-colors"
            >
              <Globe className="h-3.5 w-3.5" />
              HELP TRANSLATE →
            </a>
            <Link
              to="/contact"
              className="text-xs font-mono text-gray-400 border border-cyber-light/30 px-3 py-1.5 hover:bg-white/5 transition-colors"
            >
              CONTACT US →
            </Link>
          </div>
        </section>

        <p className="text-center text-xs text-gray-600 font-mono pt-4">
          "They said NO USER SERVICEABLE PARTS INSIDE... We took that personally."
        </p>
      </div>
    </div>
  );
}
