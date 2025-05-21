package com.dollarfunding.mca.security;

import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;

import java.util.Collection;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Core security class that implements UserDetails interface to represent an authenticated user
 * in the Spring Security context. It encapsulates user information including ID, username, password,
 * email, authorities, and account status flags.
 * 
 * This class is essential for the authentication and authorization process as it provides
 * user details to Spring Security.
 */
public class UserPrincipal implements UserDetails {

    private static final long serialVersionUID = 1L;

    private final Long id;
    private final String username;
    private final String password;
    private final String email;
    private final String firstName;
    private final String lastName;
    private final Collection<? extends GrantedAuthority> authorities;
    private final boolean enabled;
    private final boolean accountNonExpired;
    private final boolean accountNonLocked;
    private final boolean credentialsNonExpired;

    /**
     * Constructor with all fields.
     *
     * @param id                    the user ID
     * @param username              the username
     * @param password              the password (encoded)
     * @param email                 the email address
     * @param firstName             the first name
     * @param lastName              the last name
     * @param authorities           the granted authorities
     * @param enabled               whether the account is enabled
     * @param accountNonExpired     whether the account is not expired
     * @param accountNonLocked      whether the account is not locked
     * @param credentialsNonExpired whether the credentials are not expired
     */
    public UserPrincipal(Long id, String username, String password, String email, String firstName, String lastName,
                         Collection<? extends GrantedAuthority> authorities, boolean enabled, boolean accountNonExpired,
                         boolean accountNonLocked, boolean credentialsNonExpired) {
        this.id = id;
        this.username = username;
        this.password = password;
        this.email = email;
        this.firstName = firstName;
        this.lastName = lastName;
        this.authorities = authorities;
        this.enabled = enabled;
        this.accountNonExpired = accountNonExpired;
        this.accountNonLocked = accountNonLocked;
        this.credentialsNonExpired = credentialsNonExpired;
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
                user.getPassword(),
                user.getEmail(),
                user.getFirstName(),
                user.getLastName(),
                authorities,
                user.isEnabled(),
                user.isAccountNonExpired(),
                user.isAccountNonLocked(),
                user.isCredentialsNonExpired()
        );
    }

    /**
     * Creates a UserPrincipal from a User entity with additional authorities.
     *
     * @param user        the User entity
     * @param authorities additional authorities to add
     * @return a new UserPrincipal instance
     */
    public static UserPrincipal create(User user, Collection<? extends GrantedAuthority> authorities) {
        return new UserPrincipal(
                user.getId(),
                user.getUsername(),
                user.getPassword(),
                user.getEmail(),
                user.getFirstName(),
                user.getLastName(),
                authorities,
                user.isEnabled(),
                user.isAccountNonExpired(),
                user.isAccountNonLocked(),
                user.isCredentialsNonExpired()
        );
    }

    /**
     * Gets the user ID.
     *
     * @return the user ID
     */
    public Long getId() {
        return id;
    }

    /**
     * Gets the email address.
     *
     * @return the email address
     */
    public String getEmail() {
        return email;
    }

    /**
     * Gets the first name.
     *
     * @return the first name
     */
    public String getFirstName() {
        return firstName;
    }

    /**
     * Gets the last name.
     *
     * @return the last name
     */
    public String getLastName() {
        return lastName;
    }

    /**
     * Gets the full name (first name + last name).
     *
     * @return the full name, or username if first and last name are not available
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

    /**
     * Checks if the user has a specific authority.
     *
     * @param authority the authority to check
     * @return true if the user has the authority, false otherwise
     */
    public boolean hasAuthority(String authority) {
        return authorities.stream()
                .anyMatch(a -> a.getAuthority().equals(authority));
    }

    /**
     * Checks if the user has a specific role.
     *
     * @param role the role to check (with or without ROLE_ prefix)
     * @return true if the user has the role, false otherwise
     */
    public boolean hasRole(String role) {
        String roleWithPrefix = RoleConstants.addRolePrefix(role);
        return hasAuthority(roleWithPrefix);
    }

    /**
     * Checks if the user is an Operations Staff.
     *
     * @return true if the user is an Operations Staff, false otherwise
     */
    public boolean isOperationsStaff() {
        return hasAuthority(RoleConstants.ROLE_OPERATIONS_STAFF);
    }

    /**
     * Checks if the user is a System Admin.
     *
     * @return true if the user is a System Admin, false otherwise
     */
    public boolean isSystemAdmin() {
        return hasAuthority(RoleConstants.ROLE_SYSTEM_ADMIN);
    }

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
                "}";
    }

    /**
     * Builder class for UserPrincipal to facilitate creation of UserPrincipal objects.
     */
    public static class Builder {
        private Long id;
        private String username;
        private String password;
        private String email;
        private String firstName;
        private String lastName;
        private Collection<? extends GrantedAuthority> authorities;
        private boolean enabled = true;
        private boolean accountNonExpired = true;
        private boolean accountNonLocked = true;
        private boolean credentialsNonExpired = true;

        public Builder id(Long id) {
            this.id = id;
            return this;
        }

        public Builder username(String username) {
            this.username = username;
            return this;
        }

        public Builder password(String password) {
            this.password = password;
            return this;
        }

        public Builder email(String email) {
            this.email = email;
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

        public Builder accountNonLocked(boolean accountNonLocked) {
            this.accountNonLocked = accountNonLocked;
            return this;
        }

        public Builder credentialsNonExpired(boolean credentialsNonExpired) {
            this.credentialsNonExpired = credentialsNonExpired;
            return this;
        }

        public UserPrincipal build() {
            return new UserPrincipal(
                    id,
                    username,
                    password,
                    email,
                    firstName,
                    lastName,
                    authorities,
                    enabled,
                    accountNonExpired,
                    accountNonLocked,
                    credentialsNonExpired
            );
        }
    }

    /**
     * Creates a new Builder instance.
     *
     * @return a new Builder instance
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Creates a UserPrincipal for an Operations Staff user.
     *
     * @param user the User entity
     * @return a new UserPrincipal instance with Operations Staff role
     */
    public static UserPrincipal createOperationsStaffPrincipal(User user) {
        List<GrantedAuthority> authorities = List.of(
                new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF)
        );
        return create(user, authorities);
    }

    /**
     * Creates a UserPrincipal for a System Admin user.
     *
     * @param user the User entity
     * @return a new UserPrincipal instance with System Admin role
     */
    public static UserPrincipal createSystemAdminPrincipal(User user) {
        List<GrantedAuthority> authorities = List.of(
                new SimpleGrantedAuthority(RoleConstants.ROLE_SYSTEM_ADMIN),
                new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF)
        );
        return create(user, authorities);
    }
}