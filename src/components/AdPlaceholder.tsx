import { cn } from '@/lib/utils';

interface AdPlaceholderProps {
  position: 'header' | 'below-search' | 'before-download' | 'footer';
  className?: string;
}

const AdPlaceholder = ({ position, className }: AdPlaceholderProps) => {
  const heights = { header: 'h-24', 'below-search': 'h-28', 'before-download': 'h-24', footer: 'h-32' };

  return (
    <div className={cn('ads-container flex items-center justify-center transition-all duration-300 hover:border-primary/20', heights[position], className)} data-ad-position={position}>
      <div className="flex flex-col items-center gap-2 opacity-30">
        <div className="w-8 h-8 rounded-lg bg-muted/50" />
        <span className="text-xs text-muted-foreground/50 uppercase tracking-widest">Advertisement</span>
      </div>
    </div>
  );
};

export default AdPlaceholder;
