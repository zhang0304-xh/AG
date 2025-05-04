// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 设置当前活动导航项
    setActiveNavItem();
    
    // 响应式侧边栏切换
    setupResponsiveSidebar();
    
    // 检查用户认证状态
    checkAuthAndRedirect();
});

// 设置当前活动导航项
function setActiveNavItem() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

// 设置响应式侧边栏
function setupResponsiveSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    
    if (window.innerWidth <= 768) {
        sidebar.style.position = 'relative';
        mainContent.style.marginLeft = '0';
    }
    
    window.addEventListener('resize', () => {
        if (window.innerWidth <= 768) {
            sidebar.style.position = 'relative';
            mainContent.style.marginLeft = '0';
        } else {
            sidebar.style.position = 'fixed';
            mainContent.style.marginLeft = '250px';
        }
    });
}

// 检查用户认证状态并重定向
function checkAuthAndRedirect() {
    // 排除登录和注册页面，防止循环重定向
    const currentPath = window.location.pathname;
    if (currentPath === '/' || currentPath === '/register') {
        return;
    }
    
    // 检查用户信息
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}');
    
    // 如果用户未登录，重定向到登录页面
    if (!userInfo.user_id || !userInfo.username) {
        console.log('匿名用户访问，重定向到登录页面');
        window.location.href = '/';
    } else {
        // 如果用户已登录，确保用户信息与导航栏同步
        updateNavBar(userInfo);
    }
}

// 更新导航栏用户信息
function updateNavBar(userInfo) {
    const loginSection = document.getElementById('login-section');
    const userSection = document.getElementById('user-section');
    const usernameDisplay = document.getElementById('username-display');
    
    if (loginSection && userSection && usernameDisplay) {
        loginSection.style.display = 'none';
        userSection.style.display = 'block';
        usernameDisplay.textContent = userInfo.username;
    }
} 