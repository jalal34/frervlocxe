import "https://deno.land/x/xhr@0.1.0/mod.ts";
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

// Rate limiting map (simple in-memory rate limiting)
const rateLimitMap = new Map<string, { count: number; resetTime: number }>();
const RATE_LIMIT = 10; // requests per minute
const RATE_WINDOW = 60000; // 1 minute in milliseconds

function isRateLimited(ip: string): boolean {
  const now = Date.now();
  const record = rateLimitMap.get(ip);
  
  if (!record || now > record.resetTime) {
    rateLimitMap.set(ip, { count: 1, resetTime: now + RATE_WINDOW });
    return false;
  }
  
  if (record.count >= RATE_LIMIT) {
    return true;
  }
  
  record.count++;
  return false;
}

// Validate URL format and supported platforms
function validateUrl(url: string): { valid: boolean; platform?: string; error?: string } {
  if (!url || typeof url !== 'string') {
    return { valid: false, error: 'URL is required' };
  }

  const trimmedUrl = url.trim();
  
  // Basic URL validation
  try {
    new URL(trimmedUrl);
  } catch {
    return { valid: false, error: 'Invalid URL format' };
  }

  // Check for supported platforms
  const platforms = [
    { name: 'YouTube', patterns: ['youtube.com', 'youtu.be'] },
    { name: 'TikTok', patterns: ['tiktok.com'] },
    { name: 'Instagram', patterns: ['instagram.com'] },
    { name: 'Twitter', patterns: ['twitter.com', 'x.com'] },
    { name: 'Facebook', patterns: ['facebook.com', 'fb.watch'] },
    { name: 'Vimeo', patterns: ['vimeo.com'] },
  ];

  for (const platform of platforms) {
    if (platform.patterns.some(pattern => trimmedUrl.includes(pattern))) {
      return { valid: true, platform: platform.name };
    }
  }

  return { valid: false, error: 'Platform not supported' };
}

// Sanitize input to prevent injection attacks
function sanitizeInput(input: string): string {
  return input
    .replace(/[<>'"]/g, '') // Remove potentially dangerous characters
    .substring(0, 2048); // Limit length
}

serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    // Get client IP for rate limiting
    const clientIP = req.headers.get('x-forwarded-for') || 
                     req.headers.get('cf-connecting-ip') || 
                     'unknown';
    
    // Check rate limit
    if (isRateLimited(clientIP)) {
      console.log(`Rate limit exceeded for IP: ${clientIP}`);
      return new Response(
        JSON.stringify({ error: 'Too many requests. Please try again later.' }),
        { 
          status: 429, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
        }
      );
    }

    // Parse and validate request body
    let body;
    try {
      body = await req.json();
    } catch {
      return new Response(
        JSON.stringify({ error: 'Invalid request body' }),
        { 
          status: 400, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
        }
      );
    }

    const { url } = body;
    const sanitizedUrl = sanitizeInput(url || '');
    
    // Validate URL
    const validation = validateUrl(sanitizedUrl);
    if (!validation.valid) {
      console.log(`Invalid URL attempt: ${sanitizedUrl}`);
      return new Response(
        JSON.stringify({ error: validation.error }),
        { 
          status: 400, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
        }
      );
    }

    console.log(`Processing video request for platform: ${validation.platform}, URL: ${sanitizedUrl}`);

    // Mock video data for demo (in production, integrate with yt-dlp or similar)
    // This demonstrates the secure structure without exposing API keys
    const mockVideoData = {
      success: true,
      video: {
        title: `Sample Video from ${validation.platform}`,
        thumbnail: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&q=80',
        duration: '12:34',
        platform: validation.platform,
        views: Math.floor(Math.random() * 1000000).toLocaleString(),
        formats: [
          { quality: '4K Ultra HD', type: 'video', size: '420 MB', format_id: '4k' },
          { quality: '1080p Full HD', type: 'video', size: '156 MB', format_id: '1080p' },
          { quality: '720p HD', type: 'video', size: '89 MB', format_id: '720p' },
          { quality: 'MP3 320kbps', type: 'audio', size: '12 MB', format_id: 'mp3' },
        ],
      }
    };

    return new Response(
      JSON.stringify(mockVideoData),
      { 
        status: 200, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      }
    );

  } catch (error) {
    console.error('Error in fetch-video function:', error);
    return new Response(
      JSON.stringify({ error: 'An error occurred while processing your request' }),
      { 
        status: 500, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      }
    );
  }
});