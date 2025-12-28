import { Heart, Shield, Zap } from 'lucide-react';
import { useLanguage } from '@/hooks/useLanguage';
import LegalModals from './LegalModals';

const Footer = () => {
  const { t } = useLanguage();

  const features = [
    {
      icon: Zap,
      title: t('footer.lightningFast'),
      desc: t('footer.lightningFastDesc'),
      iconBg: 'bg-primary/10',
      iconColor: 'text-primary',
    },
    {
      icon: Shield,
      title: t('footer.safe'),
      desc: t('footer.safeDesc'),
      iconBg: 'bg-secondary/10',
      iconColor: 'text-secondary',
    },
    {
      icon: Heart,
      title: t('footer.free'),
      desc: t('footer.freeDesc'),
      iconBg: 'bg-accent/10',
      iconColor: 'text-accent',
    },
  ];

  const socialLinks = [
    {
      name: 'Instagram',
      url: 'https://instagram.com/oxx6k',
      icon: (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
        </svg>
      ),
    },
    {
      name: 'Telegram',
      url: 'https://t.me/oxx6k',
      icon: (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
          <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
        </svg>
      ),
    },
  ];

  return (
    <footer className="py-16 border-t border-border/30">
      <div className="container mx-auto px-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
          {features.map((feature, index) => (
            <div key={index} className="feature-card group">
              <div className={`w-14 h-14 rounded-2xl ${feature.iconBg} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300`}>
                <feature.icon className={`w-7 h-7 ${feature.iconColor}`} />
              </div>
              <h3 className="font-bold text-lg text-foreground mb-2">{feature.title}</h3>
              <p className="text-muted-foreground leading-relaxed">{feature.desc}</p>
            </div>
          ))}
        </div>

        <div className="text-center pt-8 border-t border-border/20">
          <div className="inline-flex items-center gap-3 mb-4">
            <span className="logo-text text-xl text-gradient">VEXLO</span>
          </div>
          <p className="text-sm text-muted-foreground">
            {t('footer.copyright').replace('{year}', new Date().getFullYear().toString())}
          </p>
          <p className="text-xs text-muted-foreground/50 mt-2">
            {t('footer.disclaimer')}
          </p>
          
          {/* Legal Links */}
          <div className="flex items-center justify-center mt-4">
            <LegalModals />
          </div>
          {/* Social Links */}
          <div className="flex items-center justify-center gap-4 mt-4">
            {socialLinks.map((social) => (
              <a
                key={social.name}
                href={social.url}
                target="_blank"
                rel="noopener noreferrer"
                className="w-10 h-10 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-primary hover:bg-primary hover:text-primary-foreground transition-all duration-300 hover:scale-110 hover:shadow-lg hover:shadow-primary/25"
                aria-label={social.name}
              >
                {social.icon}
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
