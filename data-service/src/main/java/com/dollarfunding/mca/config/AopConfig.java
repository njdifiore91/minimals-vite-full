package com.dollarfunding.mca.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.EnableAspectJAutoProxy;

/**
 * Configuration class to enable AspectJ support for the application.
 * 
 * This configuration enables Spring's AspectJ auto-proxy support, which allows
 * the use of AspectJ annotations for defining aspects, pointcuts, and advice.
 * It is required for the ReadOnlyRoutingAspect to function properly.
 */
@Configuration
@EnableAspectJAutoProxy
public class AopConfig {
    // No additional beans needed, just enabling AspectJ support
}