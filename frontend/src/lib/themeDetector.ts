export interface Theme {
  name: string;
  description: string;
  colors: {
    primary: string;
    secondary: string;
    accent: string;
    background: string;
    text: string;
  };
  fonts: {
    heading: string;
    body: string;
  };
  style: 'modern' | 'minimal' | 'bold' | 'playful' | 'elegant';
}

export function detectTheme(businessDescription: string): Theme {
  const desc = businessDescription.toLowerCase();

  // Pet/Cat Shop - Warm and playful
  if (desc.includes('kucing') || desc.includes('cat') || desc.includes('pet') || desc.includes('haiwan') || desc.includes('anjing') || desc.includes('dog')) {
    return {
      name: 'Purrfect Paws Theme',
      description: 'Warm oranges, soft neutrals, and rounded "friendly" UI elements',
      colors: {
        primary: '#f97316', // Orange
        secondary: '#fef3c7', // Cream
        accent: '#78350f', // Brown
        background: '#fffbeb',
        text: '#1f2937'
      },
      fonts: {
        heading: 'Quicksand',
        body: 'Nunito'
      },
      style: 'playful'
    };
  }

  // Restaurant/Food - Rich and appetizing
  if (desc.includes('makan') || desc.includes('restoran') || desc.includes('food') || desc.includes('nasi') || desc.includes('cafe') || desc.includes('kafe') || desc.includes('makanan')) {
    return {
      name: 'Tasty Bites Theme',
      description: 'Rich reds and warm colors with appetizing vibes',
      colors: {
        primary: '#dc2626', // Red
        secondary: '#fef2f2',
        accent: '#f59e0b', // Amber
        background: '#ffffff',
        text: '#1f2937'
      },
      fonts: {
        heading: 'Playfair Display',
        body: 'Lato'
      },
      style: 'bold'
    };
  }

  // Salon/Beauty - Elegant and luxurious
  if (desc.includes('salon') || desc.includes('beauty') || desc.includes('spa') || desc.includes('rambut') || desc.includes('kecantikan') || desc.includes('gunting')) {
    return {
      name: 'Glamour Touch Theme',
      description: 'Elegant pinks and golds with luxury feel',
      colors: {
        primary: '#ec4899', // Pink
        secondary: '#fdf2f8',
        accent: '#d97706', // Gold
        background: '#ffffff',
        text: '#374151'
      },
      fonts: {
        heading: 'Cormorant Garamond',
        body: 'Montserrat'
      },
      style: 'elegant'
    };
  }

  // Photography - Clean and dramatic
  if (desc.includes('photo') || desc.includes('gambar') || desc.includes('wedding') || desc.includes('fotografi') || desc.includes('kamera')) {
    return {
      name: 'Capture Moments Theme',
      description: 'Clean blacks and whites with dramatic contrast',
      colors: {
        primary: '#1f2937', // Dark gray
        secondary: '#f9fafb',
        accent: '#6366f1', // Indigo
        background: '#ffffff',
        text: '#111827'
      },
      fonts: {
        heading: 'Playfair Display',
        body: 'Inter'
      },
      style: 'minimal'
    };
  }

  // Fitness/Gym - Energetic and strong
  if (desc.includes('gym') || desc.includes('fitness') || desc.includes('sukan') || desc.includes('senaman') || desc.includes('workout')) {
    return {
      name: 'Power Fitness Theme',
      description: 'Bold reds and blacks with energetic vibes',
      colors: {
        primary: '#ef4444', // Red
        secondary: '#fef2f2',
        accent: '#f59e0b', // Orange
        background: '#111827',
        text: '#ffffff'
      },
      fonts: {
        heading: 'Bebas Neue',
        body: 'Roboto'
      },
      style: 'bold'
    };
  }

  // Tech/Software - Modern and professional
  if (desc.includes('tech') || desc.includes('software') || desc.includes('app') || desc.includes('digital') || desc.includes('IT') || desc.includes('teknologi')) {
    return {
      name: 'Digital Edge Theme',
      description: 'Modern blues and gradients with tech vibes',
      colors: {
        primary: '#3b82f6', // Blue
        secondary: '#eff6ff',
        accent: '#8b5cf6', // Purple
        background: '#f8fafc',
        text: '#0f172a'
      },
      fonts: {
        heading: 'Inter',
        body: 'Inter'
      },
      style: 'modern'
    };
  }

  // Education - Friendly and trustworthy
  if (desc.includes('tuisyen') || desc.includes('pendidikan') || desc.includes('education') || desc.includes('school') || desc.includes('kursus') || desc.includes('class')) {
    return {
      name: 'Learn & Grow Theme',
      description: 'Friendly blues and greens for learning',
      colors: {
        primary: '#2563eb', // Blue
        secondary: '#dbeafe',
        accent: '#10b981', // Green
        background: '#ffffff',
        text: '#1e293b'
      },
      fonts: {
        heading: 'Poppins',
        body: 'Open Sans'
      },
      style: 'modern'
    };
  }

  // Default Theme - Professional and versatile
  return {
    name: 'Professional Theme',
    description: 'Clean and versatile design for any business',
    colors: {
      primary: '#2563eb',
      secondary: '#f1f5f9',
      accent: '#0891b2',
      background: '#ffffff',
      text: '#1e293b'
    },
    fonts: {
      heading: 'Inter',
      body: 'Inter'
    },
    style: 'modern'
  };
}
