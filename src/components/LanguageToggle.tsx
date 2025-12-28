import { Globe } from 'lucide-react';
import { useLanguage } from '@/hooks/useLanguage';

const LanguageToggle = () => {
  const { language, setLanguage } = useLanguage();

  return (
    <div className="flex items-center rounded-xl bg-muted/40 p-1 border border-border/50 backdrop-blur-sm">
      <button
        onClick={() => setLanguage('en')}
        className={`px-3 py-2 text-sm font-medium rounded-lg transition-all duration-300 ${
          language === 'en'
            ? 'bg-primary text-background shadow-md shadow-primary/30'
            : 'text-muted-foreground hover:text-foreground'
        }`}
      >
        EN
      </button>
      <button
        onClick={() => setLanguage('ar')}
        className={`px-3 py-2 text-sm font-medium rounded-lg transition-all duration-300 ${
          language === 'ar'
            ? 'bg-primary text-background shadow-md shadow-primary/30'
            : 'text-muted-foreground hover:text-foreground'
        }`}
      >
        عربي
      </button>
    </div>
  );
};

export default LanguageToggle;
