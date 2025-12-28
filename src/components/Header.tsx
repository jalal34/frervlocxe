import { Sparkles } from 'lucide-react';
import { useLanguage } from '@/hooks/useLanguage';
import LanguageToggle from './LanguageToggle';
import ThemeToggle from './ThemeToggle';

const Header = () => {
  const { t } = useLanguage();

  return (
    <header className="relative py-4 md:py-6">
      <div className="container mx-auto px-4">
        <nav className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="relative group">
              {/* Logo Icon */}
              <div className="relative w-12 h-12 rounded-2xl bg-gradient-to-br from-primary via-primary to-secondary flex items-center justify-center overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-primary/80 to-secondary/80 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <span className="logo-text text-xl text-background relative z-10">V</span>
                {/* Animated ring */}
                <div className="absolute inset-0 rounded-2xl border-2 border-primary/50 animate-glow-pulse" />
              </div>
              {/* Status dot */}
              <div className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-green-400 border-2 border-background animate-pulse" />
            </div>
            <div>
              <h1 className="logo-text text-2xl text-gradient tracking-widest">{t('app.name')}</h1>
              <p className="text-xs text-muted-foreground tracking-wide">{t('app.tagline')}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden md:flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 backdrop-blur-sm">
              <Sparkles className="w-4 h-4 text-primary" />
              <span className="text-sm text-primary font-medium">{t('header.noWatermark')}</span>
            </div>
            <LanguageToggle />
            <ThemeToggle />
          </div>
        </nav>
      </div>
    </header>
  );
};

export default Header;
