const jwt = require('jsonwebtoken');

const authMiddleware = (req, res, next) => {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return res.status(401).json({ error: 'Unauthorized: No token provided' });
    }

    const token = authHeader.split(' ')[1];
    
    try {
        const secret = process.env.JWT_SECRET || 'super-secret-jwt-key-for-lms-development-environment';
        const decoded = jwt.verify(token, secret);
        
        req.user = {
            userId: decoded.sub,
            role: decoded.role
        };
        
        next();
    } catch (err) {
        return res.status(401).json({ error: 'Unauthorized: Invalid token' });
    }
};

module.exports = authMiddleware;
