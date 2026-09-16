# Firebase Security Rules - Complete Guide

## Firestore Security Rules

```typescript
// firestore.rules

rules_version = '2';

service cloud.firestore {
  match /databases/{database}/documents {

    // ============ HELPER FUNCTIONS ============
    
    function isAuthenticated() {
      return request.auth != null;
    }

    function isAdmin() {
      return isAuthenticated() && 
             request.auth.token.role == 'admin';
    }

    function isVendor() {
      return isAuthenticated() && 
             request.auth.token.role == 'vendor';
    }

    function isOwner(userId) {
      return isAuthenticated() && 
             request.auth.uid == userId;
    }

    function hasPermission(permission) {
      return isAuthenticated() && 
             permission in request.auth.token.permissions;
    }

    // ============ USERS COLLECTION ============
    
    match /users/{userId} {
      // Users can read their own profile
      allow read: if isOwner(userId) || isAdmin();
      
      // Users can update their own profile (limited fields)
      allow update: if isOwner(userId) &&
                       request.resource.data.keys().hasOnly([
                         'displayName', 'photoURL', 'phone', 
                         'updatedAt', 'preferences'
                       ]);
      
      // Only admin can create new users
      allow create: if isAdmin();
      
      // Only admin can delete users
      allow delete: if isAdmin();

      // ========== USER SUBCOLLECTIONS ==========
      
      match /addresses/{addressId} {
        allow read, write: if isOwner(userId);
        allow delete: if isOwner(userId);
      }

      match /orders/{orderId} {
        allow read: if isOwner(userId) || isAdmin();
      }

      match /preferences/{prefId} {
        allow read, write: if isOwner(userId);
      }
    }

    // ============ PRODUCTS COLLECTION ============
    
    match /products/{productId} {
      // Anyone can read active products
      allow read: if resource.data.isActive == true;
      
      // Vendors and admins can read all products
      allow read: if isVendor() || isAdmin();
      
      // Vendors can update their own products
      allow update: if isVendor() && 
                       resource.data.vendorId == request.auth.uid &&
                       request.resource.data.vendorId == resource.data.vendorId;
      
      // Only admin can create products
      allow create: if isAdmin();
      
      // Only vendor owner or admin can delete
      allow delete: if isAdmin() || 
                       (isVendor() && resource.data.vendorId == request.auth.uid);

      // ========== PRODUCT SUBCOLLECTIONS ==========
      
      match /reviews/{reviewId} {
        allow read: if true;
        
        allow create: if isAuthenticated() &&
                        request.resource.data.userId == request.auth.uid &&
                        request.resource.data.rating >= 1 &&
                        request.resource.data.rating <= 5;
        
        allow update, delete: if request.resource.data.userId == request.auth.uid;
      }

      match /images/{imageId} {
        allow read: if true;
        allow write: if isAdmin() || 
                        (isVendor() && resource.data.vendorId == request.auth.uid);
      }

      match /inventory/{inventoryId} {
        allow read: if isVendor() || isAdmin();
        allow write: if isVendor() || isAdmin();
      }
    }

    // ============ ORDERS COLLECTION ============
    
    match /orders/{orderId} {
      // Users can read their own orders
      allow read: if isOwner(resource.data.userId) || isAdmin();
      
      // Users can create their own orders
      allow create: if isAuthenticated() &&
                       request.resource.data.userId == request.auth.uid &&
                       request.resource.data.status == 'pending' &&
                       request.resource.data.pricing.total > 0;
      
      // Users can update their pending orders
      allow update: if (isOwner(resource.data.userId) || isAdmin()) &&
                       (resource.data.status == 'pending' ||
                        resource.data.status == 'confirmed');
      
      // Only admin can cancel/refund orders
      allow update: if isAdmin() &&
                       (request.resource.data.status == 'cancelled' ||
                        request.resource.data.status == 'refunded');
      
      allow delete: if false; // Orders are never deleted

      // ========== ORDER SUBCOLLECTIONS ==========
      
      match /items/{itemId} {
        allow read: if isOwner(get(/databases/$(database)/documents/orders/$(orderId)).data.userId) ||
                       isAdmin();
        allow write: if isAdmin();
      }

      match /payments/{paymentId} {
        allow read: if isOwner(get(/databases/$(database)/documents/orders/$(orderId)).data.userId) ||
                       isAdmin();
        allow write: if isAdmin();
      }

      match /history/{eventId} {
        allow read: if isOwner(get(/databases/$(database)/documents/orders/$(orderId)).data.userId) ||
                       isAdmin();
        allow write: if isAdmin();
      }
    }

    // ============ PAYMENTS COLLECTION ============
    
    match /payments/{paymentId} {
      // Users can read their own payments
      allow read: if isOwner(resource.data.userId) || isAdmin();
      
      // Only cloud functions can create/update payments
      allow write: if false;
    }

    // ============ CART COLLECTION ============
    
    match /carts/{userId} {
      // Users can read/write their own cart
      allow read, write: if isOwner(userId);
      
      allow delete: if isOwner(userId);
    }

    // ============ CATEGORIES COLLECTION ============
    
    match /categories/{categoryId} {
      // Anyone can read active categories
      allow read: if resource.data.isActive == true;
      
      // Only admin can write
      allow write: if isAdmin();
      
      allow delete: if isAdmin();
    }

    // ============ ADMIN COLLECTION ============
    
    match /admins/{docId} {
      // Only admin can access
      allow read, write, delete: if isAdmin();
    }

    // ============ ANALYTICS COLLECTION ============
    
    match /analytics_orders/{docId} {
      // Only admin can read
      allow read: if isAdmin();
      
      // Cloud functions write only
      allow write: if false;
    }

    // ============ DEFAULT DENY ============
    
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

## Realtime Database Rules

```json
{
  "rules": {
    "users": {
      "$userId": {
        ".read": "auth.uid === $userId || root.child('admins').child(auth.uid).exists()",
        ".write": "auth.uid === $userId || root.child('admins').child(auth.uid).exists()",
        "profile": {
          ".validate": "newData.hasChildren(['displayName', 'email'])"
        },
        "presence": {
          ".read": true,
          ".write": "auth.uid === $userId",
          ".validate": "newData.isBoolean()"
        }
      }
    },
    "presence": {
      "$userId": {
        ".read": true,
        ".write": "auth.uid === $userId",
        "status": {
          ".validate": "newData.val() === 'online' || newData.val() === 'offline'"
        }
      }
    },
    "notifications": {
      "$userId": {
        ".read": "auth.uid === $userId",
        ".write": false,
        "$notificationId": {
          ".validate": "newData.hasChildren(['message', 'timestamp'])"
        }
      }
    },
    "admin": {
      ".read": "root.child('admins').child(auth.uid).exists()",
      ".write": "root.child('admins').child(auth.uid).exists()"
    }
  }
}
```

## Storage Security Rules

```typescript
// storage.rules

rules_version = '2';

service firebase.storage {
  match /b/{bucket}/o {

    // ============ HELPER FUNCTIONS ============
    
    function isAuthenticated() {
      return request.auth != null;
    }

    function isAdmin() {
      return request.auth.token.role == 'admin';
    }

    function isVendor() {
      return request.auth.token.role == 'vendor';
    }

    // ============ PRODUCT IMAGES ============
    
    match /products/{productId}/{allPaths=**} {
      // Anyone can read product images
      allow read: if true;
      
      // Only admin or vendor owner can upload
      allow write: if (isAdmin() || isVendor()) &&
                      request.resource.size <= 5 * 1024 * 1024 && // 5MB max
                      request.resource.contentType.matches('image/.*');
    }

    // ============ USER PROFILES ============
    
    match /users/{userId}/{allPaths=**} {
      // Users can read/write their own files
      allow read, write: if request.auth.uid == userId &&
                            request.resource.size <= 2 * 1024 * 1024; // 2MB max
    }

    // ============ ORDER DOCUMENTS ============
    
    match /orders/{orderId}/{allPaths=**} {
      // Users can read their order documents
      allow read: if isAuthenticated();
      
      // Only cloud functions can write
      allow write: if false;
    }

    // ============ PUBLIC UPLOADS ============
    
    match /public/{allPaths=**} {
      allow read: if true;
      allow write: if isAuthenticated() &&
                      request.resource.size <= 10 * 1024 * 1024;
    }

    // ============ DEFAULT DENY ============
    
    match /{allPaths=**} {
      allow read, write: if false;
    }
  }
}
```

## Dynamic Security Rules

```typescript
// Dynamic rules based on custom claims
rules_version = '2';

service cloud.firestore {
  match /databases/{database}/documents {

    // Multi-level RBAC
    function hasRole(requiredRole) {
      let roles = ['customer', 'vendor', 'moderator', 'admin'];
      let userRoleIndex = roles.indexOf(request.auth.token.role);
      let requiredRoleIndex = roles.indexOf(requiredRole);
      return userRoleIndex >= requiredRoleIndex;
    }

    // Resource-based access
    function canAccessResource(resourceOwnerId) {
      return request.auth.uid == resourceOwnerId || 
             request.auth.token.role == 'admin';
    }

    // Time-based access
    function isWithinBusinessHours() {
      let now = now.minutes().toTime();
      return now.hours >= 9 && now.hours < 18;
    }

    // Data validation
    function isValidEmail(email) {
      return email.matches('^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$');
    }

    match /users/{userId} {
      allow write: if canAccessResource(userId) &&
                      isValidEmail(request.resource.data.email) &&
                      request.resource.data.email == get(/databases/$(database)/documents/users/$(userId)).data.email;
    }

    match /orders/{orderId} {
      allow write: if hasRole('admin') || 
                      (hasRole('customer') && 
                       request.resource.data.userId == request.auth.uid);
    }
  }
}
```

## Best Practices

**Authentication:**
- Always check `request.auth` for sensitive operations
- Use custom claims for role verification
- Verify token validity with admin SDK

**Authorization:**
- Implement least privilege principle
- Use helper functions for reusable logic
- Validate data structure with `.validate`
- Check field ownership for updates

**Performance:**
- Use collection-level rules when possible
- Avoid complex nested queries in rules
- Cache frequently checked data
- Use indexes for optimized rules

**Security:**
- Never trust client-side data
- Validate all incoming data
- Implement rate limiting for write operations
- Use environment-specific rules

**Testing:**
- Test rule logic with Firebase emulator
- Create unit tests for security rules
- Test edge cases and permission boundaries