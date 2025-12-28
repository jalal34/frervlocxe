import { useLanguage } from '@/hooks/useLanguage';

const platforms = [
  { name: 'YouTube', color: 'from-red-500 to-red-600' },
  { name: 'TikTok', color: 'from-pink-500 to-purple-500' },
  { name: 'Instagram', color: 'from-purple-500 to-orange-400' },
  { name: 'Twitter', color: 'from-blue-400 to-blue-500' },
  { name: 'Facebook', color: 'from-blue-600 to-blue-700' },
  { name: 'Vimeo', color: 'from-cyan-500 to-blue-500' },
];

const PlatformIcons = () => {
  const { t } = useLanguage();

  return (
    <div className="mt-10">
      <p className="text-sm text-muted-foreground/60 mb-4 uppercase tracking-wider">{t('platforms.supported')}</p>
      <div className="flex flex-wrap justify-center gap-3">
        {platforms.map((platform) => (
          <div key={platform.name} className="group relative px-4 py-2 rounded-xl bg-muted/30 border border-border/50 hover:border-primary/30 transition-all duration-300 hover:-translate-y-1 cursor-default">
            <div className={`absolute inset-0 rounded-xl bg-gradient-to-r ${platform.color} opacity-0 group-hover:opacity-10 transition-opacity duration-300`} />
            <span className="text-sm font-medium text-muted-foreground group-hover:text-foreground transition-colors relative z-10">{platform.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default PlatformIcons;
