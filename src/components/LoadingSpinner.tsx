const LoadingSpinner = () => {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-6">
      <div className="relative w-20 h-20">
        <div className="absolute inset-0 rounded-full border-4 border-muted" />
        <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-primary border-r-primary/50 animate-spin" />
        <div className="absolute inset-2 rounded-full bg-gradient-to-br from-primary/20 to-secondary/20 animate-pulse" />
        <div className="absolute inset-1/3 rounded-full bg-primary shadow-lg shadow-primary/50" />
      </div>
      <p className="text-lg font-medium text-muted-foreground">Analyzing video...</p>
      <div className="flex gap-2">
        {[0, 1, 2].map((i) => (
          <div key={i} className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
        ))}
      </div>
    </div>
  );
};

export default LoadingSpinner;
