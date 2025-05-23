package com.dollarfunding.mca.security;

import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;

import java.util.Collection;
import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;

/**
 * Core security class that implements UserDetails interface to represent an authenticated user
 * in the Spring Security context. It encapsulates user information including ID, username, password,
 * email, authorities, and account status flags.
 * 
 * <p>This class is essential for the authentication and authorization process as it provides
 * user details to Spring Security for the MCA Application Processing System.</p>
 */
public class UserPrincipal implements UserDetails {

    private static final long serialVersionUID = 1L;

    private final Long id;
    private final String username;
    private final String email;
    private final String password;
    private final Collection<? extends GrantedAuthority> authorities;
    private final boolean enabled;
    private final boolean accountNonExpired;
    private final boolean credentialsNonExpired;
    private final boolean accountNonLocked;
    private final String firstName;
    private final String lastName;

    /**
     * Private constructor used by the builder.
     */
    private UserPrincipal(Long id, String username, String email, String password,
                         Collection<? extends GrantedAuthority> authorities,
                         boolean enabled, boolean accountNonExpired,
                         boolean credentialsNonExpired, boolean accountNonLocked,
                         String firstName, String lastName) {
        this.id = id;
        this.username = username;
        this.email = email;
        this.password = password;
        this.authorities = authorities;
        this.enabled = enabled;
        this.accountNonExpired = accountNonExpired;
        this.credentialsNonExpired = credentialsNonExpired;
        this.accountNonLocked = accountNonLocked;
        this.firstName = firstName;
        this.lastName = lastName;
    }

    /**
     * Creates a UserPrincipal from a User entity.
     *
     * @param user the User entity
     * @return a new UserPrincipal instance
     */
    public static UserPrincipal create(User user) {
        List<GrantedAuthority> authorities = user.getRoles().stream()
                .map(role -> new SimpleGrantedAuthority(role.getName()))
                .collect(Collectors.toList());

        return new UserPrincipal(
                user.getId(),
                user.getUsername(),
                user.getEmail(),
                user.getPassword(),
                authorities,
                user.isEnabled(),
                user.isAccountNonExpired(),
                user.isCredentialsNonExpired(),
                user.isAccountNonLocked(),
                user.getFirstName(),
                user.getLastName()
        );
    }
    
    /**
     * Builder class for creating UserPrincipal instances.
     */
    public static class Builder {
        private Long id;
        private String username;
        private String email;
        private String password;
        private Collection<? extends GrantedAuthority> authorities;
        private boolean enabled = true;
        private boolean accountNonExpired = true;
        private boolean credentialsNonExpired = true;
        private boolean accountNonLocked = true;
        private String firstName;
        private String lastName;
        
        public Builder id(Long id) {
            this.id = id;
            return this;
        }
        
        public Builder username(String username) {
            this.username = username;
            return this;
        }
        
        public Builder email(String email) {
            this.email = email;
            return this;
        }
        
        public Builder password(String password) {
            this.password = password;
            return this;
        }
        
        public Builder authorities(Collection<? extends GrantedAuthority> authorities) {
            this.authorities = authorities;
            return this;
        }
        
        public Builder enabled(boolean enabled) {
            this.enabled = enabled;
            return this;
        }
        
        public Builder accountNonExpired(boolean accountNonExpired) {
            this.accountNonExpired = accountNonExpired;
            return this;
        }
        
        public Builder credentialsNonExpired(boolean credentialsNonExpired) {
            this.credentialsNonExpired = credentialsNonExpired;
            return this;
        }
        
        public Builder accountNonLocked(boolean accountNonLocked) {
            this.accountNonLocked = accountNonLocked;
            return this;
        }
        
        public Builder firstName(String firstName) {
            this.firstName = firstName;
            return this;
        }
        
        public Builder lastName(String lastName) {
            this.lastName = lastName;
            return this;
        }
        
        public UserPrincipal build() {
            return new UserPrincipal(
                    id,
                    username,
                    email,
                    password,
                    authorities,
                    enabled,
                    accountNonExpired,
                    credentialsNonExpired,
                    accountNonLocked,
                    firstName,
                    lastName
            );
        }
    }
    
    /**
     * Creates a new builder instance.
     *
     * @return a new builder instance
     */
    public static Builder builder() {
        return new Builder();
    }
    
    // UserDetails interface implementation
    
    @Override
    public Collection<? extends GrantedAuthority> getAuthorities() {
        return authorities;
    }

    @Override
    public String getPassword() {
        return password;
    }

    @Override
    public String getUsername() {
        return username;
    }

    @Override
    public boolean isAccountNonExpired() {
        return accountNonExpired;
    }

    @Override
    public boolean isAccountNonLocked() {
        return accountNonLocked;
    }

    @Override
    public boolean isCredentialsNonExpired() {
        return credentialsNonExpired;
    }

    @Override
    public boolean isEnabled() {
        return enabled;
    }
    
    // Additional getters
    
    public Long getId() {
        return id;
    }
    
    public String getEmail() {
        return email;
    }
    
    public String getFirstName() {
        return firstName;
    }
    
    public String getLastName() {
        return lastName;
    }
    
    /**
     * Get the full name of the user (first name + last name).
     *
     * @return the full name of the user, or username if first and last name are not available
     */
    public String getFullName() {
        if (firstName != null && lastName != null) {
            return firstName + " " + lastName;
        } else if (firstName != null) {
            return firstName;
        } else if (lastName != null) {
            return lastName;
        } else {
            return username;
        }
    }
    
    // Role and authority checking methods
    
    /**
     * Check if the user has a specific authority.
     *
     * @param authority the authority to check
     * @return true if the user has the authority, false otherwise
     */
    public boolean hasAuthority(String authority) {
        return authorities.stream()
                .anyMatch(a -> a.getAuthority().equals(authority));
    }
    
    /**
     * Check if the user has a specific role.
     *
     * @param roleName the role name to check (without ROLE_ prefix)
     * @return true if the user has the role, false otherwise
     */
    public boolean hasRole(String roleName) {
        String normalizedRoleName = RoleConstants.toSpringRole(roleName);
        return hasAuthority(normalizedRoleName);
    }
    
    /**
     * Check if the user is an Operations Staff.
     *
     * @return true if the user is an Operations Staff, false otherwise
     */
    public boolean isOperationsStaff() {
        return hasAuthority(RoleConstants.ROLE_OPERATIONS_STAFF);
    }
    
    /**
     * Check if the user is a System Admin.
     *
     * @return true if the user is a System Admin, false otherwise
     */
    public boolean isSystemAdmin() {
        return hasAuthority(RoleConstants.ROLE_SYSTEM_ADMIN);
    }
    
    // Object overrides
    
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        
        UserPrincipal that = (UserPrincipal) o;
        return Objects.equals(id, that.id);
    }
    
    @Override
    public int hashCode() {
        return Objects.hash(id);
    }
    
    @Override
    public String toString() {
        return "UserPrincipal{" +
                "id=" + id +
                ", username='" + username + '\'' +
                ", email='" + email + '\'' +
                ", enabled=" + enabled +
                ", accountNonExpired=" + accountNonExpired +
                ", credentialsNonExpired=" + credentialsNonExpired +
                ", accountNonLocked=" + accountNonLocked +
                ", firstName='" + firstName + '\'' +
                ", lastName='" + lastName + '\'' +
                "}";
    }