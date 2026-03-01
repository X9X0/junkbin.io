import { Link } from 'react-router-dom';
import { Heart, Wrench } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="border-t border-cyber-light/30 bg-cyber-darker mt-auto">
      <div className="mx-auto max-w-7xl px-4 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="col-span-1 md:col-span-2">
            <Link to="/" className="flex items-center gap-3 mb-4">
              <Wrench className="h-6 w-6 text-cyber-cyan" />
              <span className="font-display text-lg font-bold tracking-wider text-white">
                JUNK<span className="text-cyber-cyan">BIN</span>
              </span>
            </Link>
            <p className="text-gray-400 text-sm mb-4 max-w-md">
              A community-driven database for electronic component documentation.
              Supporting the Right to Repair movement by making schematics and
              component information freely accessible.
            </p>
            <div className="flex items-center gap-1 text-sm text-gray-500 font-mono">
              <span className="text-cyber-pink">&lt;</span>
              NO USER SERVICEABLE PARTS INSIDE
              <span className="text-cyber-pink">/&gt;</span>
            </div>
            <p className="text-xs text-gray-600 mt-1 font-mono">
              We took that personally.
            </p>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="font-mono text-sm font-semibold text-white mb-4 tracking-wider">
              EXPLORE
            </h3>
            <ul className="space-y-2">
              <li>
                <Link
                  to="/products"
                  className="text-sm text-gray-400 hover:text-cyber-cyan transition-colors"
                >
                  Products
                </Link>
              </li>
              <li>
                <Link
                  to="/components"
                  className="text-sm text-gray-400 hover:text-cyber-cyan transition-colors"
                >
                  Components
                </Link>
              </li>
              <li>
                <Link
                  to="/schematics"
                  className="text-sm text-gray-400 hover:text-cyber-cyan transition-colors"
                >
                  Schematics
                </Link>
              </li>
              <li>
                <Link
                  to="/submit"
                  className="text-sm text-gray-400 hover:text-cyber-cyan transition-colors"
                >
                  Contribute
                </Link>
              </li>
            </ul>
          </div>

          {/* Community */}
          <div>
            <h3 className="font-mono text-sm font-semibold text-white mb-4 tracking-wider">
              COMMUNITY
            </h3>
            <ul className="space-y-2">
              <li>
                <a
                  href="https://repair.org"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-gray-400 hover:text-cyber-cyan transition-colors"
                >
                  Right to Repair
                </a>
              </li>
              <li>
                <a
                  href="https://www.ifixit.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-gray-400 hover:text-cyber-cyan transition-colors"
                >
                  iFixit
                </a>
              </li>
              <li>
                <Link
                  to="/guidelines"
                  className="text-sm text-gray-400 hover:text-cyber-cyan transition-colors"
                >
                  Guidelines
                </Link>
              </li>
              <li>
                <Link
                  to="/docs"
                  className="text-sm text-gray-400 hover:text-cyber-cyan transition-colors"
                >
                  Documentation
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-12 pt-6 border-t border-cyber-light/20 flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex flex-col sm:flex-row items-center gap-2 sm:gap-4">
            <p className="text-xs text-gray-500 font-mono">
              &copy; {new Date().getFullYear()} Junkbin.io - Open Source
            </p>
            <span className="text-gray-600 font-mono text-xs hidden sm:inline">·</span>
            <span className="text-xs text-gray-600 font-mono">
              v{__APP_VERSION__} · {new Date(__BUILD_TIME__).toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' })} {new Date(__BUILD_TIME__).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC', hour12: false })} UTC
            </span>
          </div>
          <div className="flex items-center gap-4 sm:gap-6">
            <span className="text-xs text-gray-600 font-mono hidden sm:flex items-center gap-1">
              Press <span className="px-1.5 py-0.5 bg-cyber-dark border border-cyber-light/30 text-gray-400">?</span> for shortcuts
            </span>
            <span className="text-xs text-gray-500 font-mono flex items-center gap-1">
              Made with <Heart className="h-3 w-3 text-cyber-pink" /> for repair
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
