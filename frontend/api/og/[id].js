// Vercel Edge Function for dynamic Open Graph meta tags
// Serves OG tags for all requests, then redirects user via JavaScript

export const config = {
    runtime: 'edge',
};

export default async function handler(request) {
    const url = new URL(request.url);
    const pathParts = url.pathname.split('/');
    const id = pathParts[pathParts.length - 1];

    // Get the origin from request URL
    const origin = url.origin;
    const pageUrl = `${origin}/destination/${id}`;

    // Get optional params: user image and timestamp
    const userImageUrl = url.searchParams.get('img');
    const timestamp = url.searchParams.get('t');

    // Default values in case API fails
    let title = 'Địa điểm du lịch';
    let description = 'Khám phá với Smart Sightseeing!';
    let image = `${origin}/og-default.jpg`;

    try {
        // Backend API URL
        const BEFORE_API_URL = process.env.BEFORE_API_URL || 'https://novaaa1011-before.hf.space';

        // Fetch destination data from API
        const response = await fetch(`${BEFORE_API_URL}/destinations/${id}`, {
            headers: { 'Accept': 'application/json' }
        });

        if (response.ok) {
            const destination = await response.json();

            title = destination.name || title;

            // Use provided timestamp or current time
            const displayTime = timestamp
                ? new Date(parseInt(timestamp)).toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' })
                : new Date().toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' });

            description = `Tôi đã khám phá ${destination.name} với Smart Sightseeing lúc ${displayTime} tại ${destination.location_province || 'Việt Nam'}! 🌟`;

            // Use user's uploaded image if provided, otherwise use database image
            image = userImageUrl || destination.image_urls?.[0] || image;
        }
    } catch (error) {
        console.error('API fetch error:', error);
    }

    // Return HTML with OG tags and JavaScript redirect
    const html = `<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title} - Smart Sightseeing</title>
  
  <!-- Open Graph / Facebook -->
  <meta property="og:type" content="website">
  <meta property="og:url" content="${pageUrl}">
  <meta property="og:title" content="${title}">
  <meta property="og:description" content="${description}">
  <meta property="og:image" content="${image}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:site_name" content="Smart Sightseeing">
  <meta property="og:locale" content="vi_VN">
  
  <!-- Twitter -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="${title}">
  <meta name="twitter:description" content="${description}">
  <meta name="twitter:image" content="${image}">
  
  <!-- Redirect user to actual page -->
  <script>window.location.replace("${pageUrl}");</script>
  <meta http-equiv="refresh" content="0;url=${pageUrl}">
</head>
<body>
  <p>Đang chuyển hướng đến <a href="${pageUrl}">${title}</a>...</p>
</body>
</html>`;

    return new Response(html, {
        headers: {
            'Content-Type': 'text/html; charset=utf-8',
            'Cache-Control': 'no-cache',
        },
    });
}
