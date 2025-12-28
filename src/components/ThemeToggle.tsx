import { Sun, Moon } from 'lucide-react';
import { useTheme } from '@/hooks/useTheme';

const ThemeToggle = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="relative flex items-center justify-center w-11 h-11 rounded-xl bg-muted/40 border border-border/50 text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-all duration-300 backdrop-blur-sm overflow-hidden group"
      aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      <div className="relative w-5 h-5">
        <Sun 
          className={`w-5 h-5 absolute inset-0 transition-all duration-500 ${
            theme === 'dark' 
              ? 'rotate-0 scale-100 opacity-100' 
              : 'rotate-90 scale-0 opacity-0'
          }`} 
        />
        <Moon 
          className={`w-5 h-5 absolute inset-0 transition-all duration-500 ${
            theme === 'light' 
              ? 'rotate-0 scale-100 opacity-100' 
              : '-rotate-90 scale-0 opacity-0'
          }`} 
        />
      </div>
      
      {/* Hover glow */}
      <div className="absolute inset-0 rounded-xl bg-primary/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
    </button>
  );
};

export default ThemeToggle;
