import jsPDF from 'jspdf';

/**
 * Export chat messages to PDF with proper formatting
 * @param {Array} messages - Array of chat messages
 * @param {string} fileName - Optional custom filename
 */
export const exportChatToPDF = (messages, fileName) => {
  try {
    console.log('📄 Starting basic PDF export with', messages?.length || 0, 'messages');
    
    if (!messages || messages.length === 0) {
      throw new Error('No messages to export');
    }

    // Create new PDF document
    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4'
    });

    // PDF configuration
    const pageHeight = pdf.internal.pageSize.height;
    const pageWidth = pdf.internal.pageSize.width;
    const margin = 15;
    const maxWidth = pageWidth - (margin * 2);
    
    let yPosition = margin;
    const lineHeight = 6;
    const messageSpacing = 8;

    // Add title
    pdf.setFontSize(20);
    pdf.setFont('helvetica', 'bold');
    pdf.setTextColor(59, 130, 246); // Blue color
    pdf.text('Elva AI Chat History', margin, yPosition);
    
    yPosition += 15;
    
    // Add export date
    pdf.setFontSize(10);
    pdf.setFont('helvetica', 'normal');
    pdf.setTextColor(100, 100, 100);
    pdf.text(`Exported on: ${new Date().toLocaleString()}`, margin, yPosition);
    
    yPosition += 15;

    // Filter out system messages and process chat messages
    const chatMessages = messages.filter(msg => 
      msg && 
      !msg.isSystem && 
      !msg.id?.startsWith('gmail_debug_') && 
      !msg.id?.startsWith('gmail_auth_error_') &&
      !msg.id?.startsWith('export_success_') &&
      !msg.id?.startsWith('export_error_') &&
      !msg.id?.startsWith('export_fallback_')
    );

    console.log('📄 Filtered to', chatMessages.length, 'chat messages for export');

    if (chatMessages.length === 0) {
      // Add "no messages" text
      pdf.setFontSize(12);
      pdf.setTextColor(100, 100, 100);
      pdf.text('No chat messages to export.', margin, yPosition);
    } else {
      // Process each message
      chatMessages.forEach((message, index) => {
        try {
          // Check if we need a new page
          if (yPosition > pageHeight - 30) {
            pdf.addPage();
            yPosition = margin;
          }

          // Determine message type and content
          const isUser = message.isUser;
          const messageText = message.message || message.response || '';
          const timestamp = message.timestamp ? new Date(message.timestamp).toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
          }) : '';

          // Set styling based on message type
          if (isUser) {
            pdf.setFontSize(11);
            pdf.setFont('helvetica', 'bold');
            pdf.setTextColor(59, 130, 246); // Blue for user messages
            
            // Add "You:" label
            pdf.text('You:', margin, yPosition);
            
            pdf.setFont('helvetica', 'normal');
            pdf.setTextColor(30, 30, 30);
          } else {
            pdf.setFontSize(11);
            pdf.setFont('helvetica', 'bold');
            
            // Special styling for Gmail success messages
            if (message.isGmailSuccess) {
              pdf.setTextColor(34, 197, 94); // Green color
              pdf.text('✅ System:', margin, yPosition);
            } else {
              pdf.setTextColor(139, 92, 246); // Purple for AI messages
              pdf.text('🤖 Elva AI:', margin, yPosition);
            }
            
            pdf.setFont('helvetica', 'normal');
            pdf.setTextColor(30, 30, 30);
          }

          yPosition += lineHeight;

          // Clean and format message text
          let cleanText = messageText
            .replace(/\*\*(.*?)\*\*/g, '$1') // Remove markdown bold
            .replace(/\*(.*?)\*/g, '$1') // Remove markdown italic
            .replace(/#{1,6}\s/g, '') // Remove markdown headers
            .replace(/```[\s\S]*?```/g, '[Code Block]') // Replace code blocks
            .replace(/`([^`]+)`/g, '$1') // Remove inline code marks
            .trim();

          // Handle empty messages
          if (!cleanText) {
            cleanText = isUser ? '[Message sent]' : '[Response received]';
          }

          // Split text into lines that fit the page width
          const textLines = pdf.splitTextToSize(cleanText, maxWidth - 10);
          
          // Add each line
          textLines.forEach(line => {
            if (yPosition > pageHeight - 20) {
              pdf.addPage();
              yPosition = margin;
            }
            
            pdf.text(line, margin + 5, yPosition);
            yPosition += lineHeight;
          });

          // Add timestamp if available
          if (timestamp) {
            pdf.setFontSize(8);
            pdf.setTextColor(120, 120, 120);
            pdf.text(`${timestamp}`, margin + 5, yPosition);
            yPosition += 4;
          }

          yPosition += messageSpacing;

          // Add subtle separator line between messages
          if (index < chatMessages.length - 1) {
            pdf.setDrawColor(220, 220, 220);
            pdf.setLineWidth(0.1);
            pdf.line(margin, yPosition - 4, pageWidth - margin, yPosition - 4);
          }
        } catch (msgError) {
          console.warn('Error processing message:', msgError, message);
          // Skip this message and continue
        }
      });
    }

    // Add footer to last page
    const totalPages = pdf.internal.getNumberOfPages();
    for (let i = 1; i <= totalPages; i++) {
      pdf.setPage(i);
      pdf.setFontSize(8);
      pdf.setTextColor(150, 150, 150);
      pdf.text(
        `Page ${i} of ${totalPages} - Generated by Elva AI`, 
        margin, 
        pageHeight - 10
      );
    }

    // Generate filename with timestamp if not provided
    const timestamp = new Date().toISOString().split('T')[0];
    const finalFileName = fileName || `elva-chat-${timestamp}.pdf`;

    // Save the PDF
    pdf.save(finalFileName);

    console.log('✅ Basic PDF export completed successfully');

    return {
      success: true,
      fileName: finalFileName,
      messageCount: chatMessages.length
    };

  } catch (error) {
    console.error('❌ Basic PDF Export Error:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

/**
 * Export chat messages with enhanced formatting including markdown support
 * @param {Array} messages - Array of chat messages
 * @param {string} fileName - Optional custom filename
 */
export const exportChatToPDFEnhanced = (messages, fileName) => {
  try {
    console.log('📄 Starting enhanced PDF export with', messages?.length || 0, 'messages');
    
    if (!messages || messages.length === 0) {
      throw new Error('No messages to export');
    }

    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4'
    });

    const pageHeight = pdf.internal.pageSize.height;
    const pageWidth = pdf.internal.pageSize.width;
    const margin = 15;
    const maxWidth = pageWidth - (margin * 2);
    
    let yPosition = margin;
    const lineHeight = 6;
    const messageSpacing = 10;

    // Enhanced header with logo space
    pdf.setFillColor(59, 130, 246);
    pdf.rect(0, 0, pageWidth, 25, 'F');
    
    pdf.setFontSize(24);
    pdf.setFont('helvetica', 'bold');
    pdf.setTextColor(255, 255, 255);
    pdf.text('Elva AI Chat History', margin, 17);
    
    yPosition = 35;
    
    // Filter messages before processing
    const chatMessages = messages.filter(msg => 
      msg && 
      !msg.isSystem && 
      !msg.id?.startsWith('gmail_debug_') && 
      !msg.id?.startsWith('gmail_auth_error_') &&
      !msg.id?.startsWith('export_success_') &&
      !msg.id?.startsWith('export_error_') &&
      !msg.id?.startsWith('export_fallback_')
    );

    console.log('📄 Enhanced PDF - Filtered to', chatMessages.length, 'chat messages');

    // Add metadata
    pdf.setFontSize(10);
    pdf.setFont('helvetica', 'normal');
    pdf.setTextColor(80, 80, 80);
    
    const exportInfo = [
      `Export Date: ${new Date().toLocaleDateString()}`,
      `Export Time: ${new Date().toLocaleTimeString()}`,
      `Total Messages: ${chatMessages.length}`,
      `Session ID: Available in original chat`
    ];
    
    exportInfo.forEach(info => {
      pdf.text(info, margin, yPosition);
      yPosition += 5;
    });
    
    yPosition += 10;

    // Add separator line
    pdf.setDrawColor(200, 200, 200);
    pdf.setLineWidth(0.5);
    pdf.line(margin, yPosition, pageWidth - margin, yPosition);
    yPosition += 10;

    if (chatMessages.length === 0) {
      // Add "no messages" text
      pdf.setFontSize(12);
      pdf.setTextColor(100, 100, 100);
      pdf.text('No chat messages to export.', margin, yPosition);
    } else {
      // Process messages with enhanced formatting
      chatMessages.forEach((message, index) => {
        try {
          // Page break check
          if (yPosition > pageHeight - 40) {
            pdf.addPage();
            yPosition = margin;
          }

          // Message bubble simulation
          const isUser = message.isUser;
          const bubbleColor = isUser ? [59, 130, 246] : [139, 92, 246]; // Blue for user, purple for AI
          const textColor = [255, 255, 255];
          
          // Calculate content height
          const messageText = (message.message || message.response || '').trim();
          const textLines = pdf.splitTextToSize(messageText || '[Empty message]', maxWidth - 20);
          const bubbleHeight = Math.max(15, (textLines.length * lineHeight) + 10);
          
          // Draw message bubble background
          pdf.setFillColor(...bubbleColor);
          const bubbleX = isUser ? pageWidth - margin - (maxWidth * 0.7) : margin;
          const bubbleWidth = maxWidth * 0.7;
          
          // Rounded rectangle simulation
          pdf.roundedRect(bubbleX, yPosition - 5, bubbleWidth, bubbleHeight, 3, 3, 'F');
          
          // Add sender label
          pdf.setFontSize(9);
          pdf.setFont('helvetica', 'bold');
          pdf.setTextColor(...textColor);
          
          const senderLabel = isUser ? '👤 You' : message.isGmailSuccess ? '✅ System' : '🤖 Elva AI';
          pdf.text(senderLabel, bubbleX + 5, yPosition);
          
          yPosition += 8;
          
          // Add message content
          pdf.setFontSize(10);
          pdf.setFont('helvetica', 'normal');
          
          textLines.forEach(line => {
            pdf.text(line, bubbleX + 5, yPosition);
            yPosition += lineHeight;
          });
          
          // Add timestamp
          if (message.timestamp) {
            const timestamp = new Date(message.timestamp).toLocaleTimeString([], { 
              hour: '2-digit', 
              minute: '2-digit' 
            });
            
            pdf.setFontSize(7);
            pdf.setTextColor(200, 200, 200);
            pdf.text(timestamp, bubbleX + bubbleWidth - 25, yPosition - 2);
          }
          
          yPosition += messageSpacing;
        } catch (msgError) {
          console.warn('Error processing enhanced message:', msgError, message);
          // Skip this message and continue
        }
      });
    }

    // Enhanced footer
    const totalPages = pdf.internal.getNumberOfPages();
    for (let i = 1; i <= totalPages; i++) {
      pdf.setPage(i);
      
      // Footer background
      pdf.setFillColor(245, 245, 245);
      pdf.rect(0, pageHeight - 15, pageWidth, 15, 'F');
      
      pdf.setFontSize(8);
      pdf.setTextColor(100, 100, 100);
      pdf.text(
        `Elva AI Chat Export - Page ${i} of ${totalPages}`, 
        margin, 
        pageHeight - 8
      );
      
      pdf.text(
        new Date().toLocaleDateString(),
        pageWidth - margin - 20,
        pageHeight - 8
      );
    }

    // Generate filename
    const timestamp = new Date().toISOString().split('T')[0];
    const finalFileName = fileName || `elva-chat-${timestamp}.pdf`;

    pdf.save(finalFileName);

    console.log('✅ Enhanced PDF export completed successfully');

    return {
      success: true,
      fileName: finalFileName,
      messageCount: chatMessages.length,
      enhanced: true
    };

  } catch (error) {
    console.error('❌ Enhanced PDF Export Error:', error);
    
    // Fallback to basic export
    console.log('🔄 Falling back to basic PDF export...');
    return exportChatToPDF(messages, fileName);
  }
};