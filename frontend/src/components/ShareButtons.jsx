import { useState } from 'react';
import './ShareButtons.css';

const ShareButtons = ({ title, text, url, ogUrl, userImageUrl, timestamp, compact = false }) => {
    const [copied, setCopied] = useState(false);
    const shareUrl = url || window.location.href;

    // Check if we're in production (Vercel) - Edge Functions only work there
    const isProduction = window.location.hostname !== 'localhost' && !window.location.hostname.includes('127.0.0.1');

    // Build OG URL only for production, otherwise use regular URL
    let ogShareUrl = shareUrl;
    if (isProduction && ogUrl) {
        // Build OG URL with optional params
        const ogUrlObj = new URL(ogUrl, window.location.origin);
        if (userImageUrl) ogUrlObj.searchParams.set('img', userImageUrl);
        if (timestamp) ogUrlObj.searchParams.set('t', new Date(timestamp).getTime().toString());
        ogShareUrl = ogUrlObj.toString();
    }

    const shareText = text || title || 'Check this out!';
    const fullShareText = `${shareText}\n\n🔗 ${shareUrl}`;

    // Facebook Share - uses OG URL for proper meta tags
    const shareFacebook = () => {
        const fbUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(ogShareUrl)}`;
        window.open(fbUrl, '_blank', 'width=600,height=400');
    };

    // WhatsApp - SUPPORTS custom text!
    const shareWhatsApp = () => {
        const waUrl = `https://wa.me/?text=${encodeURIComponent(fullShareText)}`;
        window.open(waUrl, '_blank');
    };

    // Telegram - SUPPORTS custom text!
    const shareTelegram = () => {
        const tgUrl = `https://t.me/share/url?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(shareText)}`;
        window.open(tgUrl, '_blank');
    };

    // Zalo - Share via Zalo - uses OG URL for proper meta tags
    const shareZalo = () => {
        const zaloUrl = `https://zalo.me/share?url=${encodeURIComponent(ogShareUrl)}`;
        window.open(zaloUrl, '_blank', 'width=600,height=400');
    };

    // Instagram - Copy for manual share (no direct API)
    const shareInstagram = () => {
        navigator.clipboard.writeText(fullShareText).then(() => {
            alert('📋 Đã copy nội dung!\n\nMở Instagram và dán vào story hoặc bài viết.');
        }).catch(() => {
            alert('Không thể copy. Vui lòng copy thủ công.');
        });
    };

    // Copy to clipboard - User can paste anywhere!
    const handleCopy = () => {
        navigator.clipboard.writeText(fullShareText).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }).catch(() => {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = fullShareText;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        });
    };

    // Native Share (for mobile) - SUPPORTS custom text!
    const handleNativeShare = async () => {
        if (navigator.share) {
            try {
                await navigator.share({
                    title: title || 'Smart Sightseeing',
                    text: shareText,
                    url: shareUrl,
                });
            } catch (err) {
                console.log('Share cancelled');
            }
        }
    };

    return (
        <div className={`share-buttons ${compact ? 'compact' : ''}`}>
            {!compact && <span className="share-label">Chia sẻ:</span>}

            {/* Facebook - just shares link */}
            <button
                className="share-btn facebook"
                onClick={shareFacebook}
                title="Chia sẻ lên Facebook"
            >
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
                </svg>
                {!compact && <span>Facebook</span>}
            </button>

            {/* WhatsApp - WORKS with text! */}
            <button
                className="share-btn whatsapp"
                onClick={shareWhatsApp}
                title="Chia sẻ qua WhatsApp"
            >
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
                </svg>
                {!compact && <span>WhatsApp</span>}
            </button>

            {/* Telegram - WORKS with text! */}
            <button
                className="share-btn telegram"
                onClick={shareTelegram}
                title="Chia sẻ qua Telegram"
            >
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z" />
                </svg>
                {!compact && <span>Telegram</span>}
            </button>

            {/* Zalo - shares link */}
            <button
                className="share-btn zalo"
                onClick={shareZalo}
                title="Chia sẻ qua Zalo"
            >
                <svg viewBox="0 0 48 48" fill="currentColor">
                    <path d="M24 0C10.745 0 0 10.745 0 24s10.745 24 24 24 24-10.745 24-24S37.255 0 24 0zm8.32 15.36h-3.84c-.32 0-.64.32-.64.64v3.52h4.48l-.64 4.16h-3.84v11.84h-4.48V23.68h-2.88v-4.16h2.88v-4.16c0-2.88 1.92-5.44 5.44-5.44h3.52v5.44zm-14.08 5.76h5.76v11.84h-5.76v-11.84zm2.88-7.04c1.28 0 2.24.96 2.24 2.24s-.96 2.24-2.24 2.24-2.24-.96-2.24-2.24.96-2.24 2.24-2.24z" />
                </svg>
                {!compact && <span>Zalo</span>}
            </button>

            {/* Instagram - copies text for manual paste */}
            <button
                className="share-btn instagram"
                onClick={shareInstagram}
                title="Copy để chia sẻ lên Instagram"
            >
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z" />
                </svg>
                {!compact && <span>Instagram</span>}
            </button>

            {/* Copy - Always works! */}
            <button
                className={`share-btn copy ${copied ? 'copied' : ''}`}
                onClick={handleCopy}
                title="Copy nội dung"
            >
                <svg viewBox="0 0 24 24" fill="currentColor">
                    {copied ? (
                        <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                    ) : (
                        <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z" />
                    )}
                </svg>
                {!compact && <span>{copied ? 'Đã copy!' : 'Copy'}</span>}
            </button>

            {/* Native share button for mobile */}
            {navigator.share && (
                <button
                    className="share-btn native"
                    onClick={handleNativeShare}
                    title="Chia sẻ"
                >
                    <svg viewBox="0 0 24 24" fill="currentColor">
                        <path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92s2.92-1.31 2.92-2.92-1.31-2.92-2.92-2.92z" />
                    </svg>
                    {!compact && <span>Khác</span>}
                </button>
            )}
        </div>
    );
};

export default ShareButtons;
