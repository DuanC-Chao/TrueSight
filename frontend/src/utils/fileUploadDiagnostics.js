/**
 * 文件上传跨平台兼容性诊断工具
 * 用于检测和诊断Windows、macOS等平台的文件上传问题
 */

/**
 * 检测浏览器和平台信息
 */
export const detectPlatformInfo = () => {
  const userAgent = navigator.userAgent;
  const platform = navigator.platform;
  
  const info = {
    userAgent,
    platform,
    isWindows: platform.includes('Win'),
    isMac: platform.includes('Mac'),
    isLinux: platform.includes('Linux'),
    browser: {
      isChrome: userAgent.includes('Chrome'),
      isFirefox: userAgent.includes('Firefox'),
      isSafari: userAgent.includes('Safari') && !userAgent.includes('Chrome'),
      isEdge: userAgent.includes('Edg'),
      isIE: userAgent.includes('MSIE') || userAgent.includes('Trident')
    }
  };
  
  console.log('平台信息:', info);
  return info;
};

/**
 * 诊断文件对象
 */
export const diagnoseFile = (file, index = 0) => {
  const diagnosis = {
    index,
    name: file.name,
    size: file.size,
    type: file.type,
    lastModified: file.lastModified,
    isFileInstance: file instanceof File,
    isBlobInstance: file instanceof Blob,
    hasOriginFileObj: !!file.originFileObj,
    properties: {}
  };
  
  // 检查所有属性
  for (let prop in file) {
    try {
      const value = file[prop];
      if (typeof value !== 'function') {
        diagnosis.properties[prop] = value;
      }
    } catch (e) {
      diagnosis.properties[prop] = `Error: ${e.message}`;
    }
  }
  
  console.log(`文件 ${index} 诊断信息:`, diagnosis);
  return diagnosis;
};

/**
 * 诊断FormData
 */
export const diagnoseFormData = (formData) => {
  const diagnosis = {
    isFormDataInstance: formData instanceof FormData,
    entries: [],
    totalEntries: 0,
    fileEntries: 0,
    nonFileEntries: 0
  };
  
  try {
    for (let [key, value] of formData.entries()) {
      const entry = {
        key,
        valueType: typeof value,
        isFile: value instanceof File,
        isBlob: value instanceof Blob
      };
      
      if (value instanceof File) {
        entry.fileName = value.name;
        entry.fileSize = value.size;
        entry.fileType = value.type;
        diagnosis.fileEntries++;
      } else if (value instanceof Blob) {
        entry.blobSize = value.size;
        entry.blobType = value.type;
        diagnosis.fileEntries++;
      } else {
        entry.value = value;
        diagnosis.nonFileEntries++;
      }
      
      diagnosis.entries.push(entry);
      diagnosis.totalEntries++;
    }
  } catch (e) {
    diagnosis.error = e.message;
  }
  
  console.log('FormData 诊断信息:', diagnosis);
  return diagnosis;
};

/**
 * 创建跨平台兼容的文件对象
 */
export const createCompatibleFile = (originalFile, targetFileName = null) => {
  try {
    // 获取实际文件对象
    let actualFile = originalFile;
    if (originalFile.originFileObj) {
      actualFile = originalFile.originFileObj;
    } else if (originalFile.file) {
      actualFile = originalFile.file;
    }
    
    // 验证文件对象
    if (!(actualFile instanceof File) && !(actualFile instanceof Blob)) {
      throw new Error('无效的文件对象');
    }
    
    // 处理文件名
    let fileName = targetFileName || actualFile.name || originalFile.name || 'unknown_file';
    
    // 清理文件名
    fileName = fileName.replace(/[\\/:*?"<>|]/g, '_');
    
    // 确保有扩展名
    if (!fileName.includes('.')) {
      const mimeType = actualFile.type || '';
      if (mimeType === 'text/plain') {
        fileName += '.txt';
      } else if (mimeType === 'application/pdf') {
        fileName += '.pdf';
      } else if (mimeType === 'text/html') {
        fileName += '.html';
      } else {
        fileName += '.txt'; // 默认
      }
    }
    
    // 创建新的File对象确保兼容性
    const compatibleFile = new File([actualFile], fileName, {
      type: actualFile.type || 'application/octet-stream',
      lastModified: actualFile.lastModified || Date.now()
    });
    
    console.log('创建兼容文件:', {
      original: actualFile.name,
      compatible: compatibleFile.name,
      size: compatibleFile.size,
      type: compatibleFile.type
    });
    
    return compatibleFile;
  } catch (error) {
    console.error('创建兼容文件失败:', error);
    throw error;
  }
};

/**
 * 创建跨平台兼容的FormData
 */
export const createCompatibleFormData = (data, files) => {
  const formData = new FormData();
  
  // 添加非文件数据
  if (data) {
    Object.keys(data).forEach(key => {
      if (data[key] !== undefined && data[key] !== null) {
        formData.append(key, data[key]);
      }
    });
  }
  
  // 添加文件
  if (files && Array.isArray(files)) {
    files.forEach((file, index) => {
      try {
        const compatibleFile = createCompatibleFile(file);
        formData.append('files', compatibleFile);
      } catch (error) {
        console.error(`处理文件 ${index} 失败:`, error);
      }
    });
  }
  
  return formData;
};

/**
 * 全面的上传前诊断
 */
export const performUploadDiagnostics = (files, additionalData = {}) => {
  console.log('=== 文件上传诊断开始 ===');
  
  // 平台信息
  const platformInfo = detectPlatformInfo();
  
  // 文件诊断
  const fileDiagnoses = files.map((file, index) => diagnoseFile(file, index));
  
  // FormData诊断
  const formData = createCompatibleFormData(additionalData, files);
  const formDataDiagnosis = diagnoseFormData(formData);
  
  const overallDiagnosis = {
    platform: platformInfo,
    files: fileDiagnoses,
    formData: formDataDiagnosis,
    summary: {
      totalFiles: files.length,
      validFiles: fileDiagnoses.filter(f => f.isFileInstance || f.isBlobInstance).length,
      platformWarnings: [],
      recommendations: []
    }
  };
  
  // 生成警告和建议
  if (platformInfo.isWindows) {
    overallDiagnosis.summary.platformWarnings.push('Windows平台：注意文件路径分隔符和文件名字符限制');
    overallDiagnosis.summary.recommendations.push('确保文件名不包含特殊字符: \\/:*?"<>|');
  }
  
  if (platformInfo.browser.isIE) {
    overallDiagnosis.summary.platformWarnings.push('Internet Explorer：FormData支持有限');
    overallDiagnosis.summary.recommendations.push('建议使用现代浏览器进行文件上传');
  }
  
  const invalidFiles = fileDiagnoses.filter(f => !f.isFileInstance && !f.isBlobInstance);
  if (invalidFiles.length > 0) {
    overallDiagnosis.summary.platformWarnings.push(`发现 ${invalidFiles.length} 个无效文件对象`);
    overallDiagnosis.summary.recommendations.push('检查文件选择逻辑和Upload组件配置');
  }
  
  console.log('=== 诊断完成 ===');
  console.log('总体诊断报告:', overallDiagnosis);
  
  return overallDiagnosis;
};

/**
 * 简化的上传测试函数
 */
export const testFileUpload = async (files, uploadUrl, additionalData = {}) => {
  console.log('=== 开始文件上传测试 ===');
  
  // 执行诊断
  const diagnosis = performUploadDiagnostics(files, additionalData);
  
  try {
    // 创建兼容的FormData
    const formData = createCompatibleFormData(additionalData, files);
    
    console.log('发送请求到:', uploadUrl);
    console.log('FormData内容总结:', diagnosis.formData);
    
    const response = await fetch(uploadUrl, {
      method: 'POST',
      body: formData
    });
    
    const result = await response.json();
    
    console.log('上传响应:', result);
    console.log('=== 文件上传测试完成 ===');
    
    return {
      success: response.ok,
      diagnosis,
      response: result,
      httpStatus: response.status
    };
  } catch (error) {
    console.error('上传测试失败:', error);
    return {
      success: false,
      diagnosis,
      error: error.message
    };
  }
};

const fileUploadDiagnostics = {
  detectPlatformInfo,
  diagnoseFile,
  diagnoseFormData,
  createCompatibleFile,
  createCompatibleFormData,
  performUploadDiagnostics,
  testFileUpload
};

export default fileUploadDiagnostics; 